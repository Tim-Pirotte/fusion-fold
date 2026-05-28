from typing import Type, NamedTuple
import functools
import time
import uuid

import redis as r

import settings as s

class DB(NamedTuple):
    sessions: r.Redis
    session_ttl: int

def get_db(settings: s.Settings) -> DB:
    return DB(
        r.Redis(
            host=settings.redis_host, 
            port=settings.redis_port, 
            db=settings.redis_db,
            decode_responses=True,
        ),
        settings.session_ttl,
    )

class DataBaseError(Exception):
    pass

def handle_redis_errors(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except r.RedisError as e:
            raise DataBaseError("Database operation failed") from e
        
    return wrapper

def retry_on_error(retries: int, delay_s: float, exceptions: Type[BaseException] | tuple[Type[BaseException], ...]):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions:                    
                    if attempt == retries:
                        raise

                    time.sleep(delay_s)

            raise AssertionError('Unreachable')

        return wrapper
    return decorator


@handle_redis_errors
@retry_on_error(1, 2, (r.ConnectionError, r.TimeoutError))
def create_session(db: DB, data: str) -> str:
    session_id = str(uuid.uuid4())
    db.sessions.setex(session_id, db.session_ttl, data)

    return session_id

@handle_redis_errors
@retry_on_error(1, 2, (r.ConnectionError, r.TimeoutError))
def get_session(db: DB, session_id: str) -> str | None:
    pipe = db.sessions.pipeline()
    pipe.get(session_id)
    pipe.delete(session_id)

    return pipe.execute()[0]
