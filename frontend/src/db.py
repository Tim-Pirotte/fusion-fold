from typing import Type, NamedTuple
import functools
import time
import uuid

import redis as r

import settings as s

WRITE_USER = 'write'
READ_DELETE_USER = 'read_delete'
    
def get_connection(settings: s.Settings, username: str) -> r.Redis:
    return r.Redis(
        host=settings.redis_host, 
        port=settings.redis_port, 
        db=settings.redis_db,
        username=settings.__getattribute__(f'redis_{username}_username'),
        password=settings.__getattribute__(f'redis_{username}_password'),
        decode_responses=True,
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
def create_session(settings: s.Settings, data: str) -> str:
    session_id = str(uuid.uuid4())
    
    connection = get_connection(settings, WRITE_USER)
    connection.setex(session_id, settings.session_ttl, data)

    return session_id

@handle_redis_errors
@retry_on_error(1, 2, (r.ConnectionError, r.TimeoutError))
def get_session(settings: s.Settings, session_id: str) -> str | None:
    connection = get_connection(settings, READ_DELETE_USER)
    
    pipe = connection.pipeline()
    pipe.get(session_id)
    pipe.delete(session_id)

    return pipe.execute()[0]
