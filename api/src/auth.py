from datetime import datetime, timedelta, timezone
from typing import Any
import secrets
import hashlib

import jwt

def hash_password(password: str) -> bytes:
    salt = secrets.token_bytes(32)

    # https://stackoverflow.com/questions/64399830/what-are-recommended-minimum-parameters-for-hashlib-scrypt
    key = hashlib.scrypt(
        password.encode(),
        salt=salt,
        n=16384,
        r=8,
        p=1,
        maxmem=32 * 1024 * 1024,
        dklen=64
    )

    return salt + key

def get_auth_token(account_id: int) -> str:
    expiration = datetime.now(timezone.utc) + timedelta(days=1)

    token_data = {
        'account_id': account_id,
        'exp': expiration,
    }

    return jwt.encode(token_data, 'secret', algorithm='HS256')

def get_auth_token_data(token: str) -> dict[str, Any] | None:
    try:
        return jwt.decode(token, 'secret', algorithm='HS256')
    except jwt.PyJWTError:
        return None
