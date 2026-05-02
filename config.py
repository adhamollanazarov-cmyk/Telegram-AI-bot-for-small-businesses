from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    BOT_TOKEN: str
    GROQ_API_KEY: str
    DATABASE_URL: str = "postgresql+asyncpg://postgres:160607@localhost:5432/botdb"
    SYNC_DATABASE_URL: str = "postgresql+psycopg2://postgres:160607@localhost:5432/botdb"
    OWNER_TELEGRAM_ID: str = ""  # запасной владелец из .env

    class Config:
        env_file = ".env"

settings = Settings()