import json
import typing
import logging
import asyncio

import pydantic as p
import fastapi as fa
from fastapi.middleware.cors import CORSMiddleware
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature

import db
import auth as a
import mail as m
import models as mo
import folding as f
import settings as s

logger = logging.getLogger()
logging.basicConfig(level=logging.INFO)

app = fa.FastAPI(title='RNA Folding API')

origins = ['http://localhost:8000']

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=['GET', 'POST', 'PATCH'],
    allow_headers=['*'],
)

settings = s.Settings()
serializer = URLSafeTimedSerializer('TODO Change')

@app.exception_handler(db.DataBaseError)
async def database_error_handler(*_):
    logger.error("Database operation failed", exc_info=True)

    raise fa.HTTPException(status_code=503, detail='Database service unavailable')

class SessionRequest(p.BaseModel):
    sequence: str = p.Field(min_length=settings.min_seq_len, max_length=settings.max_seq_len, pattern='^[AUGC]*$')
    folds_to_generate: int = p.Field(ge=settings.min_folds, le=settings.max_folds)
    steps_per_fold: int = p.Field(ge=settings.min_steps, le=settings.max_steps)
    return_noise: bool

class SessionResponse(p.BaseModel):
    sessionId: str

@app.post(
    '/v1/folding-sessions',
    response_model=SessionResponse,
    tags=['folding'],
    summary='Creates a folding session',
    description='Creates a new folding session that can be used for streaming at /v1/folding-sessions/{session_id}',
)
async def create_folding_session(payload: SessionRequest):
    session_id = db.create_session(settings, payload.model_dump_json())

    return { 'sessionId': session_id }

@app.get(
    '/v1/folding-sessions/{session_id}',
    tags=['folding'],
    summary='Streams a folding session',
    description='Streams a submitted folding session as server-sent events',
)
async def stream_folding(
    session_id: str,
):
    session_str = db.get_session(settings, session_id)

    if not session_str:
        raise fa.HTTPException(status_code=404, detail='Session not found')

    session = SessionRequest.model_validate_json(session_str)

    return fa.responses.StreamingResponse(folding_streamer(session), media_type='text/event-stream')

def folding_streamer(session: SessionRequest) -> typing.Iterator[str]:
    try:
        for fold in f.folding_iterator(
            session.sequence,
            session.folds_to_generate,
            session.steps_per_fold,
            session.return_noise,
        ):
            yield f'data: {json.dumps(fold)}\n\n'

        logger.info('finished folding')

        yield 'event: end\ndata: null\n\n'

    except (GeneratorExit, asyncio.CancelledError):
        logger.info('ending folding early due to client disconnect')

class CreateAccountRequest(p.BaseModel):
    display_name: str
    mail: str

@app.post(
    '/v1/accounts',
    tags=['accounts'],
    summary='Creates a new account',
    description='Creates an account and sends an e-mail to verify the address and set a password',
)
async def create_account(request: CreateAccountRequest):
    account_id = await db.create_account(settings, request.display_name, request.mail)

    if account_id:
        token = serializer.dumps({'account_id': account_id, 'action': 'verify_and_set_password'})
        m.send_mock_verification_mail(request.mail, token)

        return 200

    return 403

class CompleteAccountRequest(p.BaseModel):
    password: str

@app.patch(
    '/v1/accounts/{token}',
    tags=['accounts'],
    summary='Completes a created account',
    description='Completes an account with a password and changes the account status from unverified to enabled',
    responses={
        400: { 'description': 'Invalid token or password does not meet requirements' },
        410: { 'description': 'Token expired' },
        422: { 'description': 'Account does not exist or status is not \'unverified\'' },
    },
)
async def complete_account(token: str, request: CompleteAccountRequest, response: fa.Response):
    try:
        data = serializer.loads(token, max_age=86400)
    except SignatureExpired:
        return fa.Response(status_code=fa.status.HTTP_410_GONE)
    except BadSignature:
        return fa.Response(status_code=fa.status.HTTP_400_BAD_REQUEST)

    if data.get('action') != 'verify_and_set_password':
        return fa.Response(status_code=fa.status.HTTP_400_BAD_REQUEST)

    account_id = data.get('account_id')

    if account_id is None:
        return fa.Response(status_code=fa.status.HTTP_400_BAD_REQUEST)

    if not (8 <= len(request.password) <= 16):
        return fa.Response(status_code=fa.status.HTTP_400_BAD_REQUEST)

    hashed_password = a.hash_password(request.password)

    if not await db.complete_account(settings, account_id, hashed_password):
        return fa.Response(status_code=fa.status.HTTP_422_UNPROCESSABLE_ENTITY)

    res = fa.Response(status_code=fa.status.HTTP_200_OK)
    set_auth_cookie(res, account_id)

    return res

def set_auth_cookie(response: fa.Response, account_id: int):
    response.set_cookie(
        key='auth_token',
        value=a.get_auth_token(account_id),
        httponly=True,
        secure=False, # To allow HTTP
        samesite='lax'
    )

async def get_current_account(auth_token: str = fa.Cookie(default='')) -> mo.Account:
    data = a.get_auth_token_data(auth_token)

    if data is None:
        raise fa.HTTPException(status_code=fa.status.HTTP_401_UNAUTHORIZED)

    account_id: str | None = data.get('account_id')

    if account_id is None:
        raise fa.HTTPException(status_code=fa.status.HTTP_401_UNAUTHORIZED)

    account = await db.get_account(settings, int(account_id))

    if account is None:
        raise fa.HTTPException(status_code=fa.status.HTTP_404_NOT_FOUND)

    return account

class LoginRequest(p.BaseModel):
    mail: str
    password: str

@app.post(
    '/v1/accounts/login',
    tags=['accounts'],
    summary='Logs in to an account',
    description='Validates credentials and sets an auth cookie on success',
    responses={
        400: { 'description': 'Invalid password, e-mail or acccount is disabled' },
    },
)
async def login(request: LoginRequest):
    account = await db.get_account_by_mail(settings, request.mail)

    if account is None:
        return fa.Response(status_code=fa.status.HTTP_400_BAD_REQUEST)

    if account.status != mo.AccountStatus.enabled:
        return fa.Response(status_code=fa.status.HTTP_400_BAD_REQUEST)

    if not a.verify_password(request.password, account.password_hash):
        return fa.Response(status_code=fa.status.HTTP_400_BAD_REQUEST)

    response = fa.Response(status_code=fa.status.HTTP_200_OK)
    set_auth_cookie(response, account.id)

    return response

@app.post(
    '/v1/accounts/logout',
    tags=['accounts'],
    summary='Logs out the current account',
    description='Clears the auth_token cookie so the user has to login again',
)
async def logout():
    response = fa.Response(status_code=fa.status.HTTP_200_OK)
    response.delete_cookie(key='auth_token', httponly=True, samesite='lax')

    return response

class GetAccountResponse(p.BaseModel):
    display_name: str
    mail: str

@app.get(
    '/v1/accounts/',
    response_model=GetAccountResponse,
    tags=['accounts'],
    summary='Retrieves account data of the current session',
    description='Retrieves the account data of the currently logged in user',
)
async def get_account(account: mo.Account = fa.Depends(get_current_account)):
    return {
        "display_name": account.display_name,
        "mail": account.mail,
    }
