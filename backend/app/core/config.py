from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "ZN API"
    APP_ENV: str = "development"
    APP_DEBUG: bool = True

    HOST: str = "127.0.0.1"
    PORT: int = 8000

    class Config:
        env_file = ".env"


settings = Settings()