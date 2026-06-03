import json
import typing
import logging
import secrets
import hashlib
import asyncio

import pydantic as p
import fastapi as fa
from fastapi.middleware.cors import CORSMiddleware
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature

import db
import mail as m
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
)
async def complete_account(token: str, request: CompleteAccountRequest):
    try:
        data = serializer.loads(token, max_age=86400)
    except SignatureExpired:
        raise fa.HTTPException(status_code=fa.status.HTTP_410_GONE)
    except BadSignature:
        raise fa.HTTPException(status_code=fa.status.HTTP_400_BAD_REQUEST)

    if data.get('action') != 'verify_and_set_password':
        raise fa.HTTPException(status_code=fa.status.HTTP_400_BAD_REQUEST)

    account_id = data.get('account_id')

    if account_id is None:
        raise fa.HTTPException(status_code=fa.status.HTTP_400_BAD_REQUEST)

    if not (8 <= len(request.password) <= 16):
        raise fa.HTTPException(status_code=fa.status.HTTP_400_BAD_REQUEST)

    salt = secrets.token_bytes(32)

    # https://stackoverflow.com/questions/64399830/what-are-recommended-minimum-parameters-for-hashlib-scrypt
    key = hashlib.scrypt(
        request.password.encode(),
        salt=salt,
        n=16384,
        r=8,
        p=1,
        maxmem=32 * 1024 * 1024,
        dklen=64
    )

    password_hash = salt + key

    if not await db.complete_account(settings, account_id, password_hash):
        raise fa.HTTPException(status_code=fa.status.HTTP_422_UNPROCESSABLE_ENTITY)

    return fa.Response(status_code=fa.status.HTTP_200_OK)
