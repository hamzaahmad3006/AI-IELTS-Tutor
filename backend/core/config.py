"""Application settings, loaded from environment (12-factor)."""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # App
    app_env: str = "development"
    api_v1_prefix: str = "/v1"
    log_level: str = "INFO"

    # Security
    jwt_secret: str = "change_me_in_production"
    jwt_alg: str = "HS256"
    access_token_ttl_min: int = 15
    refresh_token_ttl_days: int = 30

    # Database
    # Defaults to a local SQLite file so the backend runs out of the box.
    # In production set DATABASE_URL to the Supabase PostgreSQL async URL, e.g.
    #   postgresql+asyncpg://user:pass@db.supabase.co:5432/postgres
    database_url: str = "sqlite+aiosqlite:///./dev.db"

    # AI (provider-agnostic)
    ai_provider: str = "groq"
    groq_api_key: str = ""

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")


@lru_cache
def get_settings() -> Settings:
    return Settings()
