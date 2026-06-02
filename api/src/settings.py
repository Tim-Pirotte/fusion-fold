import pydantic as p
import pydantic_settings as ps

class Settings(ps.BaseSettings):
    redis_host: str
    redis_port: int = p.Field(ge=0, le=65_535)
    redis_db: int = p.Field(ge=0, le=15)

    postgres_host: str
    postgres_port: int = p.Field(ge=0, le=65_535)
    postgres_db: str

    session_ttl: int = p.Field(ge=0)
    
    min_seq_len: int = p.Field(ge=1)
    max_seq_len: int

    min_folds: int = p.Field(ge=1)
    max_folds: int = p.Field()

    min_steps: int = p.Field(ge=1)
    max_steps: int = p.Field()
    
    @p.model_validator(mode='after')
    def validate_ranges(self) -> 'Settings':
        fields = ['seq_len', 'folds', 'steps']

        for field in fields:
            min_v = getattr(self, f'min_{field}')
            max_v = getattr(self, f'max_{field}')
            
            if max_v < min_v:
                raise ValueError(f'{field} has a higher max than min')
        
        return self

    class Config:
        env_file = '.env'
