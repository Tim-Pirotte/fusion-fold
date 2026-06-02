from pathlib import Path
from typing import Type
import functools
import time
import uuid

import redis as r
import sqlalchemy as al

import settings as s

_session_makers: dict[str, al.orm.sessionmaker] = {}

class DataBaseError(Exception):
    pass
    
def get_redis_connection(settings: s.Settings, username: str) -> r.Redis:
    try:
        return r.Redis(
            host=settings.redis_host, 
            port=settings.redis_port, 
            db=settings.redis_db,
            username=username,
            password=Path(f'/run/secrets/redis_{username}').read_text().strip(),
            decode_responses=True,
        )
    except FileNotFoundError as e:
        raise DataBaseError(f'No credentials for Redis user {username}') from e
    
async def get_postgres_connection(settings: s.Settings, username: str) -> al.ext.asyncio.AsyncSession:
    global _session_makers
    
    if username in _session_makers:
        session_maker = _session_makers['username']
    else:
        try:
            password = Path(f'/run/secrets/postgres_{username}').read_text().strip()
        except FileNotFoundError as e:
            raise DataBaseError(f'No credentials for Postgres user {username}') from e
        
        engine = al.ext.asyncio.create_async_engine(
            f'postgresql+asyncpg://{username}:{password}@{settings.postgres_host}:{settings.postgres_port}/{settings.postgres_db}',
            pool_size=settings.postgres_pool_size,
            max_overflow=settings.postgres_max_overflow,
        )
        
        session_maker = al.orm.sessionmaker(
            bind=engine,
            class_=al.ext.asyncio.AsyncSession,
            expire_on_commit=False,
        )
        
        _session_makers['username'] = session_maker
    
    async with session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            raise DataBaseError('Database operation failed') from e

def handle_redis_errors(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except r.RedisError as e:
            raise DataBaseError('Database operation failed') from e
        
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
    
    connection = get_redis_connection(settings, 'write')
    connection.setex(session_id, settings.session_ttl, data)

    return session_id

@handle_redis_errors
@retry_on_error(1, 2, (r.ConnectionError, r.TimeoutError))
def get_session(settings: s.Settings, session_id: str) -> str | None:
    connection = get_redis_connection(settings, 'read_delete')
    
    pipe = connection.pipeline()
    pipe.get(session_id)
    pipe.delete(session_id)

    return pipe.execute()[0]
