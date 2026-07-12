from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from .env / environment."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ─── App ───────────────────────────────────────────
    APP_NAME: str = "ZN API"
    APP_ENV: str = "development"
    APP_DEBUG: bool = True

    HOST: str = "127.0.0.1"
    PORT: int = 8000

    # ─── Database (PostgreSQL + PostGIS) ───────────────
    DB_DSN: str = "postgresql+psycopg2://zn:zn@localhost:5432/zn"
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10

    # ─── Tests ─────────────────────────────────────────
    TEST_DB_DSN: str = "postgresql+psycopg2://zn:zn@localhost:5432/zn_test"


settings = Settings()
