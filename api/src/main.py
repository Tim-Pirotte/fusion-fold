import json
import typing
import logging
import asyncio
from pathlib import Path

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
    allow_methods=['GET', 'POST', 'PATCH', 'PUT'],
    allow_headers=['*'],
)

settings = s.Settings()
serializer = URLSafeTimedSerializer(
    Path('/run/secrets/serializer_secret').read_text(encoding='utf-8').strip(),
)

async def get_current_account(auth_token: str = fa.Cookie(default='')) -> int:
    data = a.get_auth_token_data(settings, auth_token)

    if data is None:
        raise fa.HTTPException(status_code=fa.status.HTTP_401_UNAUTHORIZED)

    account_id: str | None = data.get('account_id')

    if account_id is None:
        raise fa.HTTPException(status_code=fa.status.HTTP_401_UNAUTHORIZED)

    try:
        return int(account_id)
    except ValueError as e:
        raise fa.HTTPException(status_code=fa.status.HTTP_401_UNAUTHORIZED) from e

protected = fa.APIRouter(
    dependencies=[fa.Depends(get_current_account)],
    responses={
        401: { 'description': 'Missing or invalid auth cookie' },
    },
)

@app.exception_handler(db.DataBaseError)
async def database_error_handler(*_):
    logger.error("Database operation failed", exc_info=True)

    raise fa.HTTPException(status_code=503, detail='Database service unavailable')

class SessionRequest(p.BaseModel):
    display_name: str = p.Field(
        min_length=settings.min_seq_display_name_len,
        max_length=settings.max_seq_display_name_len,
    )

    sequence: str = p.Field(
        min_length=settings.min_seq_len,
        max_length=settings.max_seq_len,
        pattern='^[AUGC]*$'
    )

    folds_to_generate: int = p.Field(ge=settings.min_folds, le=settings.max_folds)
    steps_per_fold: int = p.Field(ge=settings.min_steps, le=settings.max_steps)
    return_noise: bool

class SessionResponse(p.BaseModel):
    sessionId: str

@protected.post(
    '/v1/folding-sessions',
    response_model=SessionResponse,
    tags=['folding'],
    summary='Creates a folding session',
    description='Creates a new folding session that can be used for streaming at'
                ' /v1/folding-sessions/{session_id}',
)
async def create_folding_session(payload: SessionRequest):
    session_id = db.create_session(settings, payload.model_dump_json())

    return { 'sessionId': session_id }

@protected.get(
    '/v1/folding-sessions/{session_id}',
    tags=['folding'],
    summary='Streams a folding session',
    description='Streams a submitted folding session as server-sent events',
)
async def stream_folding(
    request: fa.Request,
    session_id: str,
    account_id: int = fa.Depends(get_current_account),
):
    session_str = db.get_session(settings, session_id)

    if not session_str:
        return fa.Response(status_code=fa.status.HTTP_404_NOT_FOUND)

    session = SessionRequest.model_validate_json(session_str)

    return fa.responses.StreamingResponse(
        folding_streamer(request, account_id, session),
        media_type='text/event-stream',
    )

async def folding_streamer(
    request: fa.Request,
    account_id: int,
    session: SessionRequest,
) -> typing.AsyncIterator[str]:
    last_fold = None

    for fold in f.folding_iterator(
        session.sequence,
        session.folds_to_generate,
        session.steps_per_fold,
        session.return_noise,
    ):
        if await request.is_disconnected():
            logger.info('ending folding early due to client disconnect')

            return

        last_fold = fold

        yield f'data: {json.dumps(fold)}\n\n'

    yield 'event: end\ndata: null\n\n'

    logger.info('finished folding')

    if last_fold is not None:
        await db.save_prediction(
            settings,
            account_id,
            session.display_name,
            session.sequence,
            last_fold['coords'],
        )

@protected.get(
    '/v1/predictions',
    tags=['folding'],
    summary='Retrieves the prediction history of the user',
    description='Retrieves the'
                ' display_name, date (created_at) and id'
                f' of the last (limited to {settings.max_predictions_saved}) predictions'
                ' of the logged in user',
    responses={
        404: {'description': 'The logged in account does not exist or is disabled'}
    }
)
async def get_predictions(account_id: int = fa.Depends(get_current_account)):
    predictions = await db.get_predictions(settings, account_id)

    if predictions is None:
        response = fa.Response(status_code=fa.status.HTTP_404_NOT_FOUND)

        return response

    return {
        'predictions': [
            {
                'id': prediction.id,
                'display_name': prediction.display_name,
                'created_at': prediction.created_at,
            }
            for prediction in predictions
        ],
    }

@protected.get(
    '/v1/predictions/{prediction_id}/sequence',
    tags=['folding'],
    summary='Retrieves a prediction sequence',
    description='Retrieves the sequence of a prediction of the logged in user',
    responses={
        404: {
            'description': 'The prediction does not exist'
                           ' or the logged in account does not exist or is disabled',
        }
    }
)
async def get_sequence(prediction_id: int, account_id: int = fa.Depends(get_current_account)):
    sequence = await db.get_sequence(settings, account_id, prediction_id)

    if sequence is None:
        return fa.Response(status_code=fa.status.HTTP_404_NOT_FOUND)

    return {'sequence': sequence}

class CoordsResponseCoord(p.BaseModel):
    position: int
    x: float
    y: float
    z: float

class GetCoordsResponse(p.BaseModel):
    coords: list[CoordsResponseCoord]

@protected.get(
    '/v1/predictions/{prediction_id}/coords',
    tags=['folding'],
    summary='Retrieves prediction coordinates',
    description='Retrieves the coordinates of a prediction of the logged in user',
    response_model=GetCoordsResponse,
    responses={
        404: {'description': 'The logged in account does not exist or is disabled'}
    }
)
async def get_coords(prediction_id: int, account_id: int = fa.Depends(get_current_account)):
    coords = await db.get_coords(settings, account_id, prediction_id)

    if coords is None:
        return fa.Response(status_code=fa.status.HTTP_404_NOT_FOUND)

    return {'coords': coords}

class CreateAccountRequest(p.BaseModel):
    display_name: str = p.Field(
        min_length=settings.min_display_name_len, max_length=settings.max_display_name_len,
    )

    mail: str = p.Field(min_length=settings.min_mail_len, max_length=settings.max_mail_len)

@app.post(
    '/v1/accounts',
    tags=['accounts'],
    summary='Creates a new account',
    description='Creates an account and sends an e-mail to verify the address and set a password',
    status_code=fa.status.HTTP_202_ACCEPTED,
    responses={
        403: {'description': 'An account is already registered for this e-mail'},
    },
)
async def create_account(request: CreateAccountRequest):
    account_id = await db.create_account(settings, request.display_name, request.mail)

    if account_id is None:
        return fa.Response(status_code=fa.status.HTTP_403_FORBIDDEN)

    token = serializer.dumps({'account_id': account_id, 'action': 'verify_and_set_password'})
    m.send_mock_verification_mail(request.mail, token)

    return fa.Response(status_code=fa.status.HTTP_202_ACCEPTED)

class CompleteAccountRequest(p.BaseModel):
    password: str = p.Field(
        min_length=settings.min_password_len, max_length=settings.max_password_len,
    )

@app.patch(
    '/v1/accounts/{token}',
    tags=['accounts'],
    summary='Completes a created account',
    description='Completes an account with a password'
                ' and changes the account status from unverified to enabled',
    status_code=fa.status.HTTP_204_NO_CONTENT,
    responses={
        400: {'description': 'Invalid token'},
        410: {'description': 'Token expired'},
        403: {'description': 'Account does not exist or is not unverified'},
    },
)
async def complete_account(token: str, request: CompleteAccountRequest):
    try:
        data = serializer.loads(token, max_age=settings.serializer_validity_seconds)
    except SignatureExpired:
        return fa.Response(status_code=fa.status.HTTP_410_GONE)
    except BadSignature:
        return fa.Response(status_code=fa.status.HTTP_400_BAD_REQUEST)

    if data.get('action') != 'verify_and_set_password':
        return fa.Response(status_code=fa.status.HTTP_400_BAD_REQUEST)

    account_id = data.get('account_id')

    if account_id is None:
        return fa.Response(status_code=fa.status.HTTP_400_BAD_REQUEST)

    hashed_password = a.hash_password(settings, request.password)

    if not await db.complete_account(settings, account_id, hashed_password):
        return fa.Response(status_code=fa.status.HTTP_403_FORBIDDEN)

    res = fa.Response(status_code=fa.status.HTTP_204_NO_CONTENT)
    set_auth_cookie(res, account_id)

    return res

def set_auth_cookie(response: fa.Response, account_id: int):
    response.set_cookie(
        key='auth_token',
        value=a.get_auth_token(settings, account_id),
        httponly=True,
        secure=False, # To allow HTTP
        samesite='lax'
    )

    # For the client to check if it is logged in
    response.set_cookie(
        key='logged_in',
        httponly=False,
        secure=False,
        samesite='lax'
    )

class LoginRequest(p.BaseModel):
    mail: str = p.Field(
        min_length=settings.min_mail_len, max_length=settings.max_mail_len,
    )

    password: str = p.Field(
        min_length=settings.min_password_len, max_length=settings.max_password_len,
    )

@app.post(
    '/v1/accounts/login',
    tags=['accounts'],
    summary='Logs in to an account',
    description='Validates credentials and sets an auth cookie on success',
    status_code=fa.status.HTTP_204_NO_CONTENT,
    responses={
        400: { 'description': 'Invalid password, e-mail or acccount is disabled' },
    },
)
async def login(request: LoginRequest):
    account = await db.get_account_by_mail(settings, request.mail)

    if account is None:
        return fa.Response(status_code=fa.status.HTTP_400_BAD_REQUEST)

    if account.status != mo.AccountStatus.ENABLED:
        return fa.Response(status_code=fa.status.HTTP_400_BAD_REQUEST)

    if not a.verify_password(settings, request.password, account.password_hash):
        return fa.Response(status_code=fa.status.HTTP_400_BAD_REQUEST)

    response = fa.Response(status_code=fa.status.HTTP_204_NO_CONTENT)
    set_auth_cookie(response, account.id)

    return response

@app.post(
    '/v1/accounts/logout',
    tags=['accounts'],
    summary='Logs out the current account',
    description='Clears the auth_token cookie so the user has to login again',
    status_code=fa.status.HTTP_204_NO_CONTENT,
)
async def logout():
    response = fa.Response(status_code=fa.status.HTTP_204_NO_CONTENT)

    response.delete_cookie(key='auth_token')
    response.delete_cookie(key='logged_in')

    return response

class GetAccountResponse(p.BaseModel):
    display_name: str
    mail: str

@protected.get(
    '/v1/accounts/',
    response_model=GetAccountResponse,
    tags=['accounts'],
    summary='Retrieves account data of the current session',
    description='Retrieves the account data of the currently logged in user',
    responses={
        404: {'description': 'Account does not exist or is not enabled'},
    },
)
async def get_account(account_id: int = fa.Depends(get_current_account)):
    account = await db.get_account(settings, account_id)

    if account is None or account.status != mo.AccountStatus.ENABLED:
        return fa.Response(status_code=fa.status.HTTP_404_NOT_FOUND)

    return {
        'display_name': account.display_name,
        'mail': account.mail,
    }

@protected.delete(
    '/v1/accounts/',
    tags=['accounts'],
    summary='Deletes the account of the current session',
    description='Deletes the account data of the currently logged in user and logs the user out',
    status_code=fa.status.HTTP_204_NO_CONTENT,
    responses={
        404: {'description': 'Account does not exist or is not enabled'},
    },
)
async def delete_account(account_id: int = fa.Depends(get_current_account)):
    if not await db.delete_account(settings, account_id):
        return fa.Response(status_code=fa.status.HTTP_404_NOT_FOUND)

    return await logout()

class UpdateDisplayNameRequest(p.BaseModel):
    display_name: str = p.Field(
        min_length=settings.min_display_name_len, max_length=settings.max_display_name_len,
    )

@protected.put(
    '/v1/accounts/display-name',
    tags=['accounts'],
    summary='Change the account display name of the current session',
    description='Changes the account display name of the currently logged in user',
    status_code=fa.status.HTTP_204_NO_CONTENT,
    responses={
        404: {'description': 'Account does not exist or is not enabled'},
    },
)
async def change_display_name(
    request: UpdateDisplayNameRequest, account_id: int = fa.Depends(get_current_account)
):
    if not await db.change_account_display_name(
        settings, account_id, request.display_name,
    ):
        return fa.Response(status_code=fa.status.HTTP_404_NOT_FOUND)

    return fa.Response(status_code=fa.status.HTTP_204_NO_CONTENT)

class ResetPasswordMailRequest(p.BaseModel):
    mail: str = p.Field(min_length=settings.min_mail_len, max_length=settings.max_mail_len)

@app.post(
    '/v1/accounts/password-reset',
    tags=['accounts'],
    summary='Sends a password reset e-mail',
    description='Sends a password reset e-mail if the e-mail is linked to a user',
    status_code=fa.status.HTTP_202_ACCEPTED,
)
async def send_reset_mail(request: ResetPasswordMailRequest):
    account = await db.get_account_by_mail(settings, request.mail)

    if account is None:
        return fa.Response(status_code=fa.status.HTTP_202_ACCEPTED)

    token = serializer.dumps({'account_id': account.id, 'action': 'reset_password'})
    m.send_mock_reset_password_mail(request.mail, token)

    return fa.Response(status_code=fa.status.HTTP_202_ACCEPTED)

class ResetPasswordRequest(p.BaseModel):
    password: str = p.Field(
        min_length=settings.min_password_len, max_length=settings.max_password_len,
    )

# In a real production app you should probably invalidate the token after use
@app.put(
    '/v1/accounts/password/{token}',
    tags=['accounts'],
    summary='Resets the password',
    description='Resets the password of the account'
                ' linked to the e-mail the verification was send to'
                ' and logs the user in',
    status_code=fa.status.HTTP_204_NO_CONTENT,
    responses={
        400: {'description': 'Invalid token'},
        410: {'description': 'Token expired'},
        422: {'description': 'Account does not exist or is not enabled'},
    },
)
async def reset_password(token: str, request: ResetPasswordRequest):
    try:
        data = serializer.loads(token, max_age=settings.serializer_validity_seconds)
    except SignatureExpired:
        return fa.Response(status_code=fa.status.HTTP_410_GONE)
    except BadSignature:
        return fa.Response(status_code=fa.status.HTTP_400_BAD_REQUEST)

    if data.get('action') != 'reset_password':
        return fa.Response(status_code=fa.status.HTTP_400_BAD_REQUEST)

    account_id = data.get('account_id')

    if account_id is None:
        return fa.Response(status_code=fa.status.HTTP_400_BAD_REQUEST)

    hashed_password = a.hash_password(settings, request.password)

    if not await db.reset_password(settings, account_id, hashed_password):
        return fa.Response(status_code=fa.status.HTTP_422_UNPROCESSABLE_ENTITY)

    res = fa.Response(status_code=fa.status.HTTP_204_NO_CONTENT)
    set_auth_cookie(res, account_id)

    return res

app.include_router(protected)
