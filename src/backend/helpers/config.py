from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    
    # Database configurations
    DB_USER: str
    DB_PASSWORD: str
    DB_HOST: str
    DB_PORT: str
    DB_NAME: str
    DB_URL: str

    # Google OAuth
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = ""
    ENCRYPTION_KEY: str = ""

    # Batch screening scheduler
    SCREENING_POLL_INTERVAL_MINUTES: int = 15
    NEW_CANDIDATE_THRESHOLD: int = 10
    NEW_ASSESSMENT_THRESHOLD: int = 5

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
