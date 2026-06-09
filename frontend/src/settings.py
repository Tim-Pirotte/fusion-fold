import pydantic as p
import pydantic_settings as ps

class Settings(ps.BaseSettings):
    # This could be removed by using a reverse proxy using nginx in the docker compose so
    # the same endpoints are used between it and Kubernetes but I don't have time to do that
    api: str = p.Field(min_length=1)

    class Config:
        env_file = '.env'
