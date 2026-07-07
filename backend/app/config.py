"""
Single source of truth for all environment variables.
Every other module imports from here — no os.getenv() calls anywhere else.
 
Usage:
    from app.config import settings
    settings.qdrant_url
"""
 
from pydantic_settings import BaseSettings, SettingsConfigDict
 
 
class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )
 
    # SEC EDGAR (contact info for User-Agent header)
    sec_user_name: str
    sec_user_email: str

    # OpenAI
    openai_api_key: str

    # Qdrant
    qdrant_url: str
    qdrant_api_key: str = ""  # empty string for local Docker (no auth)

    # Cohere
    cohere_api_key: str
 
 
settings = Settings()