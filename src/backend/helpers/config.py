from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    
    # Database configurations
    DB_USER: str
    DB_PASSWORD: str
    DB_HOST: str
    DB_PORT: str
    DB_NAME: str
    DB_URL: str


    class Config:
        env_file = ".env"

def get_settings():
    return Settings()
