"""Application configuration."""
import os
from pathlib import Path
from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

# Load .env from current directory, parent directory, or backend directory
current_dir = Path.cwd()
env_paths = [
    current_dir / ".env",
    current_dir.parent / ".env",
    Path(__file__).resolve().parent.parent.parent / ".env",
    Path(__file__).resolve().parent.parent.parent.parent / ".env",
]

for env_path in env_paths:
    if env_path.exists():
        load_dotenv(env_path, override=False)


class Settings(BaseSettings):
    """Runtime configuration loaded from environment variables."""
    model_config = SettingsConfigDict(env_file=(".env", "../.env", "backend/.env"), extra="ignore")
    anthropic_api_key: str = ""
    groq_api_key: str = ""
    gemini_api_key: str = ""
    database_url: str = "sqlite+aiosqlite:///./data/mitra.db"
    redis_url: str = "redis://localhost:6379/0"
    claude_model: str = "claude-sonnet-4-5-20250929"
    groq_model: str = "llama-3.3-70b-versatile"
    gemini_model: str = "gemini-2.5-flash"
    voice_transcription_model: str = "whisper-large-v3-turbo"


def get_settings() -> Settings:
    # Always reload to pick up fresh environment variables
    for env_path in env_paths:
        if env_path.exists():
            load_dotenv(env_path, override=False)
    return Settings()
