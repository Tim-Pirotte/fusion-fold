from contextlib import asynccontextmanager
from pathlib import Path
from typing import Type
from enum import Enum
import functools
import time
import uuid

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
import sqlalchemy as al
import redis as r

import settings as s
import models as m

_redis_clients: dict[str, r.Redis] = {}
_session_makers: dict[str, async_sessionmaker] = {}

class DataBaseError(Exception):
    pass

def get_redis_connection(settings: s.Settings, username: str) -> r.Redis:
    if username in _redis_clients:
        return _redis_clients[username]

    try:
        password = Path(f'/run/secrets/redis_{username}').read_text().strip()
    except FileNotFoundError as e:
        raise DataBaseError(f'No credentials for Redis user {username}') from e

    client = r.Redis(
        host=settings.redis_host,
        port=settings.redis_port,
        db=settings.redis_db,
        username=username,
        password=password,
        decode_responses=True,
    )

    _redis_clients[username] = client

    return client

@asynccontextmanager
async def get_postgres_connection(settings: s.Settings, username: str) -> AsyncSession:
    if username in _session_makers:
        session_maker = _session_makers[username]
    else:
        try:
            password = Path(f'/run/secrets/postgres_{username}').read_text().strip()
        except FileNotFoundError as e:
            raise DataBaseError(f'No credentials for Postgres user {username}') from e

        engine = create_async_engine(
            f'postgresql+asyncpg://{username}:{password}@{settings.postgres_host}:{settings.postgres_port}/{settings.postgres_db}',
            pool_size=settings.postgres_pool_size,
            max_overflow=settings.postgres_max_overflow,
        )

        session_maker = async_sessionmaker(
            bind=engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

        _session_makers[username] = session_maker

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

async def test_postgres(settings: s.Settings) -> bool:
    async with get_postgres_connection(settings, 'app_default') as connection:
        result = await connection.execute(al.text("SELECT 1;"))

        return result.scalar() == 1

class CreateAccountResult(Enum):
    OK                  = 1
    ALREADY_EXISTS      = 2
    RESENT_VERIFICATION = 3

async def create_account(settings: s.Settings, display_name: str, mail: str) -> (CreateAccountResult, int | None):
    async with get_postgres_connection(settings, 'app_default') as connection:
        existing = await connection.execute(al.select(m.Account).where(m.Account.mail == mail))
        existing_account = existing.scalar_one_or_none()

        if existing_account:
            if existing_account.status == m.AccountStatus.unverified:
                existing_account.display_name = display_name

                return CreateAccountResult.RESENT_VERIFICATION, existing_account.id

            return CreateAccountResult.ALREADY_EXISTS, None

        account = m.Account(
            display_name=display_name,
            mail=mail,
            status=m.AccountStatus.unverified
        )

        connection.add(account)
        await connection.flush()

        return CreateAccountResult.OK, account.id
