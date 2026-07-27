"""Application configuration loaded from environment / .env file."""
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env", env_file_encoding="utf-8", extra="ignore"
    )

    database_url: str = (
        "postgresql+psycopg2://postgres:root@localhost:5432/pharma_complaints"
    )

    # Never hard-code the key here — this file is committed. It is read from .env.
    groq_api_key: str = ""
    # Fast, cheap model for structured field extraction. The brief named gemma2-9b-it,
    # which Groq has since decommissioned; llama-3.1-8b-instant is its stated successor.
    groq_extraction_model: str = "llama-3.1-8b-instant"
    # llama-3.3-70b-versatile handles the reasoning-heavy nodes (root cause, CAPA).
    groq_reasoning_model: str = "llama-3.3-70b-versatile"

    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    max_upload_mb: int = 10

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def llm_live(self) -> bool:
        """True when a Groq key is present, so the agent runs against real models."""
        return bool(self.groq_api_key.strip())


@lru_cache
def get_settings() -> Settings:
    return Settings()
