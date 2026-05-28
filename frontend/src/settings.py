import pydantic as p
import pydantic_settings as ps

class Settings(ps.BaseSettings):
    redis_host: str = 'localhost'
    redis_port: int = p.Field(default=6379, ge=0, le=65_535)
    redis_db: int = p.Field(default=0, ge=0, le=15)
    redis_password: str = p.Field()

    session_ttl: int = p.Field(default=60, ge=0)
    
    min_seq_len: int = p.Field(default=2, ge=1)
    max_seq_len: int = p.Field(default=1024)

    min_folds: int = p.Field(default=1, ge=1)
    max_folds: int = p.Field(default=9)

    min_steps: int = p.Field(default=1, ge=1)
    max_steps: int = p.Field(default=25)
    
    @p.model_validator(mode='after')
    def validate_ranges(self) -> 'Settings':
        fields = ['seq_len', 'folds', 'steps']

        for field in fields:
            min_v = getattr(self, f'min_{field}')
            max_v = getattr(self, f'max_{field}')
            
            if max_v < min_v:
                raise ValueError(f"{field} has a higher max than min")
        
        return self

    class Config:
        env_file = '.env'

def get_settings():
    return Settings()
