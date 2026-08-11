"""Application configuration."""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration loaded from environment variables."""
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    anthropic_api_key: str = ""
    groq_api_key: str = ""
    gemini_api_key: str = ""
    database_url: str = "sqlite+aiosqlite:///./data/insightforge.db"
    redis_url: str = "redis://localhost:6379/0"
    # Current documented Sonnet alias/version; override when an account exposes a newer model.
    claude_model: str = "claude-sonnet-4-5-20250929"
    groq_model: str = "openai/gpt-oss-20b"
    gemini_model: str = "gemini-3.6-flash"


@lru_cache
def get_settings() -> Settings:
    return Settings()
