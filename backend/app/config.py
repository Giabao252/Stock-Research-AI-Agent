"""
app/config.py
 
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

    #other keys
 
 
settings = Settings()