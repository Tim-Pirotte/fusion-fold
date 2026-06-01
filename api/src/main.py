import json
import typing
import logging
import asyncio

import pydantic as p
import fastapi as fa

import db
import folding as f
import settings as s

logger = logging.getLogger()
logging.basicConfig(level=logging.INFO)

app = fa.FastAPI(title='RNA Folding API')

settings = s.Settings()

@app.exception_handler(db.DataBaseError)
async def database_error_handler(request: fa.Request, exc: db.DataBaseError):
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
    '/v1/folding-sessions/', 
    response_model=SessionResponse,
)
async def generate_folding_session(payload: SessionRequest):
    session_id = db.create_session(settings, payload.model_dump_json())
    
    return { 'sessionId': session_id }

@app.get('/v1/folding-sessions/{session_id}')
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
