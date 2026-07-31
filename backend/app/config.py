"""
Single source of truth for all environment variables.
Every other module imports from here — no os.getenv() calls anywhere else.
 
Usage:
    from app.config import settings
    settings.qdrant_url
"""
 
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parent.parent / ".env",
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

    # Alpha Vantage
    alpha_vantage_key: str

    # Tavily
    tavily_api_key: str

    #Redis
    upstash_redis_url: str
    upstash_redis_token: str

    # MCP servers
    mcp_server_url: str

    # Agent SDK
    claude_model: str = "haiku"


settings = Settings()