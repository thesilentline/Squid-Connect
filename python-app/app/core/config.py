from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "Squid Connect"
    API_V1_STR: str = "/api/v1"
    DATABASE_URL: str = "postgresql+asyncpg://admin_user:user123@postgres:5432/chatbot"
    
    # Secret key for API key encryption / hash derivation
    SECRET_KEY: str = "default_ilis_secret_key_32b"
    ENCRYPTION_KEY: str = ""
    
    # Default fallback OpenAI API key (optional)
    OPENAI_API_KEY: str = ""

    # Event Publisher / Collection Event Webhook
    COLLECTION_EVENT_URL: str = "http://java-app:8081/ilis/api/v1/collectionEvent"
    COLLECTION_EVENT_ENABLED: bool = True
    COLLECTION_EVENT_TIMEOUT_SECONDS: float = 3.0

    # Max multi-turn messages limit
    MAX_HISTORY_MESSAGES: int = 5

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
