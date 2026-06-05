import secrets
import hashlib

import pydantic as p
import pydantic_settings as ps

class Settings(ps.BaseSettings):
    serializer_validity_seconds: int = p.Field(ge=1)

    scrypt_salt_bytes: int = p.Field(ge=1)
    scrypt_n_pow_2: int = p.Field(ge=1)
    scrypt_r: int = p.Field(ge=1)
    scrypt_p: int = p.Field(ge=1)
    scrypt_max_mem_mb: int
    scrypt_dklen: int = p.Field(ge=1)

    jwt_algorithm: str
    jwt_validity_days: int = p.Field(ge=1)

    redis_host: str
    redis_port: int = p.Field(ge=0, le=65_535)
    redis_db: int = p.Field(ge=0, le=15)

    postgres_host: str
    postgres_port: int = p.Field(ge=0, le=65_535)
    postgres_db: str
    postgres_pool_size: int = p.Field(ge=1)
    postgres_max_overflow: int = p.Field(ge=-1)

    min_password_len: int = p.Field(ge=1, le=255)
    max_password_len: int = p.Field(le=255)

    min_mail_len: int = p.Field(ge=1, le=255)
    max_mail_len: int = p.Field(le=255)

    min_display_name_len: int = p.Field(ge=1, le=255)
    max_display_name_len: int = p.Field(le=255)

    session_ttl: int = p.Field(ge=0)

    min_seq_len: int = p.Field(ge=1)
    max_seq_len: int

    min_folds: int = p.Field(ge=1)
    max_folds: int = p.Field()

    min_steps: int = p.Field(ge=1)
    max_steps: int = p.Field()

    @p.model_validator(mode='after')
    def validate_ranges(self) -> 'Settings':
        fields = [
            'password_len',
            'mail_len',
            'display_name_len',
            'display_name_len',
            'seq_len',
            'folds',
            'steps',
        ]

        for field in fields:
            min_v = getattr(self, f'min_{field}')
            max_v = getattr(self, f'max_{field}')

            if max_v < min_v:
                raise ValueError(f'{field} has a higher max than min')

        return self

    @p.model_validator(mode='after')
    def validate_max_mem_mb(self) -> 'Settings':
        min_memory = 128 * 2**self.scrypt_n_pow_2 * self.scrypt_r * self.scrypt_p
        min_memory_mb = min_memory / (1024**2)

        if self.scrypt_max_mem_mb < min_memory_mb:
            raise ValueError(
                f'scrypt_max_mem_mb should be at least {min_memory_mb} (128 * n * r * p)',
            )

        salt = secrets.token_bytes(self.scrypt_salt_bytes)

        try:
            hashlib.scrypt(
                ('a' * self.max_password_len).encode(),
                salt=salt,
                n=2**self.scrypt_n_pow_2,
                r=self.scrypt_r,
                p=self.scrypt_p,
                maxmem=self.scrypt_max_mem_mb * 1024 * 1024,
                dklen=self.scrypt_dklen,
            )
        except ValueError as e:
            raise ValueError('scrypt_max_mem_mb is too low for the given parameters') from e

        return self

    class Config:
        env_file = '.env'
