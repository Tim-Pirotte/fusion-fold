from contextlib import asynccontextmanager
from pathlib import Path
from typing import Type
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
        password = Path(f'/run/secrets/redis_{username}').read_text(encoding='utf-8').strip()
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
            password = Path(f'/run/secrets/postgres_{username}').read_text(encoding='utf-8').strip()
        except FileNotFoundError as e:
            raise DataBaseError(f'No credentials for Postgres user {username}') from e

        engine = create_async_engine(
            f'postgresql+asyncpg://{username}:{password}'
            f'@{settings.postgres_host}:{settings.postgres_port}'
            f'/{settings.postgres_db}',

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

def retry_on_error(
    retries: int,
    delay_s: float,
    exceptions: Type[BaseException] | tuple[Type[BaseException], ...],
):
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

async def save_prediction(
    settings: s.Settings,
    account_id: int,
    display_name: str,
    rna_sequence: str,
    coords: list[list[float]],
):
    async with get_postgres_connection(settings, 'predictions_i') as connection:
        converted_coords = []

        for i, coord in enumerate(coords):
            converted_coords.append(
                m.PredictionCoordinate(position=i, x=coord[0], y=coord[1], z=coord[2]),
            )

        prediction = m.Prediction(
            account_id=account_id,
            display_name=display_name,
            rna_sequence=rna_sequence,
            coordinates=converted_coords,
        )

        connection.add(prediction)

async def get_predictions(settings: s.Settings, account_id: int) -> list[m.Prediction] | None:
    async with get_postgres_connection(settings, 'predictions_s') as connection:
        account = await connection.get(m.Account, account_id)

        if account is None or account.status != m.AccountStatus.ENABLED:
            return None

        stmt = (
            al.select(m.Prediction)
                .where(m.Prediction.account_id == account_id)
                .order_by(m.Prediction.created_at.desc())
                .limit(settings.max_prediction_results)
        )

        return (await connection.execute(stmt)).scalars().all()

async def get_sequence(settings: s.Settings, account_id: int, prediction_id: int) -> str | None:
    async with get_postgres_connection(settings, 'predictions_s') as connection:
        account = await connection.get(m.Account, account_id)

        if account is None or account.status != m.AccountStatus.ENABLED:
            return None

        stmt = (
            al.select(m.Prediction.rna_sequence)
                .where(m.Prediction.account_id == account_id)
                .where(m.Prediction.id == prediction_id)
        )

        return (await connection.execute(stmt)).scalars().one_or_none()

async def create_account(settings: s.Settings, display_name: str, mail: str) -> int | None:
    async with get_postgres_connection(settings, 'accounts_siu') as connection:
        existing = await connection.execute(al.select(m.Account).where(m.Account.mail == mail))
        existing_account = existing.scalar_one_or_none()

        if existing_account:
            if existing_account.status == m.AccountStatus.UNVERIFIED:
                existing_account.display_name = display_name

                return existing_account.id

            return None

        account = m.Account(
            display_name=display_name,
            mail=mail,
            status=m.AccountStatus.UNVERIFIED,
        )

        connection.add(account)
        await connection.flush()

        return account.id

async def complete_account(settings: s.Settings, account_id: int, password_hash: bytes) -> bool:
    async with get_postgres_connection(settings, 'accounts_su') as connection:
        account = await connection.get(m.Account, account_id)

        if account is None:
            return False

        if account.status != m.AccountStatus.UNVERIFIED:
            return False

        account.password_hash = password_hash
        account.status = m.AccountStatus.ENABLED

        return True

async def get_account(settings: s.Settings, account_id: int) -> m.Account | None:
    async with get_postgres_connection(settings, 'accounts_s') as connection:
        return await connection.get(m.Account, account_id)

async def get_account_by_mail(settings: s.Settings, mail: str) -> m.Account | None:
    async with get_postgres_connection(settings, 'accounts_s') as connection:
        account = await connection.execute(
            al.select(m.Account).where(m.Account.mail == mail),
        )

        return account.scalar_one_or_none()

async def delete_account(settings: s.Settings, account_id: int) -> bool:
    async with get_postgres_connection(settings, 'accounts_sd') as connection:
        result = await connection.execute(
            al.delete(m.Account)
                .where(m.Account.id == account_id)
                .where(m.Account.status == m.AccountStatus.ENABLED),
        )

        return result.rowcount == 1

async def change_account_display_name(settings: s.Settings, account_id: int, display_name) -> bool:
    async with get_postgres_connection(settings, 'accounts_su') as connection:
        result = await connection.execute(
            al.update(m.Account)
                .where(m.Account.id == account_id)
                .where(m.Account.status == m.AccountStatus.ENABLED)
                .values(display_name=display_name),
        )

        return result.rowcount == 1

async def reset_password(settings: s.Settings, account_id: int, password_hash: bytes) -> bool:
    async with get_postgres_connection(settings, 'accounts_su') as connection:
        account = await connection.get(m.Account, account_id)

        if account is None:
            return False

        if account.status != m.AccountStatus.ENABLED:
            return False

        account.password_hash = password_hash

        return True
