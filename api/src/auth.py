from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
import secrets
import hashlib

import jwt

import settings as s

_jwt_secret = None

def hash_password(settings: s.Settings, password: str) -> bytes:
    salt = secrets.token_bytes(settings.scrypt_salt_bytes)

    key = hashlib.scrypt(
        password.encode(),
        salt=salt,
        n=2 ** settings.scrypt_n_pow_2,
        r=settings.scrypt_r,
        p=settings.scrypt_p,
        maxmem=settings.scrypt_max_mem_mb * 1024 * 1024,
        dklen=settings.scrypt_dklen,
    )

    return salt + key

def verify_password(settings: s.Settings, password: str, hash: bytes) -> bool:
    salt = hash[:settings.scrypt_salt_bytes]
    expected_key = hash[settings.scrypt_salt_bytes:]

    actual_key = hashlib.scrypt(
        password.encode(),
        salt=salt,
        n=2 ** settings.scrypt_n_pow_2,
        r=settings.scrypt_r,
        p=settings.scrypt_p,
        maxmem=settings.scrypt_max_mem_mb * 1024 * 1024,
        dklen=settings.scrypt_dklen,
    )

    return secrets.compare_digest(actual_key, expected_key)

def get_auth_token(settings: s.Settings, account_id: int) -> str:
    expiration = datetime.now(timezone.utc) + timedelta(days=settings.jwt_validity_days)

    token_data = {
        'account_id': account_id,
        'exp': expiration,
    }

    return jwt.encode(token_data, get_jwt_secret(), algorithm=settings.jwt_algorithm)

def get_auth_token_data(settings: s.Settings, token: str) -> dict[str, Any] | None:
    try:
        return jwt.decode(token, get_jwt_secret(), algorithms=[settings.jwt_algorithm])
    except jwt.PyJWTError:
        return None

def get_jwt_secret():
    global _jwt_secret

    if _jwt_secret is None:
        _jwt_secret = Path(f'/run/secrets/jwt_secret').read_text().strip()

    return _jwt_secret
