from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(BASE_DIR / ".env"), extra="ignore")

    PROJECT_NAME: str = "event-site-backend"
    API_V1_PREFIX: str = "/api"
    DEBUG: bool = False

    DATABASE_URL: str = (
        "postgresql+psycopg2://postgres:postgres@localhost:5432/event_site"
    )


settings = Settings()
