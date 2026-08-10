"""Application settings, loaded from environment (12-factor)."""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

from core.environment import Environment


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # App
    app_env: str = "development"
    api_v1_prefix: str = "/v1"
    log_level: str = "INFO"

    #: Comma-separated origins allowed to call this API. The wildcard is a
    #: development convenience and is refused in staging and production, where
    #: it is both a security hole and -- combined with credentials -- rejected
    #: by browsers anyway.
    cors_origins: str = "*"

    #: Run periodic maintenance jobs in this process. Off by default: with
    #: several API instances every one of them would start a scheduler, and
    #: while the database lock makes that safe, it is still N processes waking
    #: up to do nothing. Enable it on one instance, or on a dedicated worker.
    jobs_enabled: bool = False

    #: OTLP endpoint for traces, e.g. http://localhost:4318/v1/traces.
    #: Blank disables tracing entirely -- creating spans with nowhere to send
    #: them costs work and buffers into a queue nobody drains.
    otel_endpoint: str = ""
    otel_service_name: str = "ai-ielts-tutor-api"

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

    # Voice: speech-to-text. Defaults to the mock so nothing bills by accident;
    # set STT_PROVIDER=deepgram and DEEPGRAM_API_KEY in .env to enable.
    stt_provider: str = "mock"
    deepgram_api_key: str = ""
    deepgram_model: str = "nova-2"

    # Voice: text-to-speech. Same default, same reason.
    tts_provider: str = "mock"
    elevenlabs_api_key: str = ""
    elevenlabs_voice_id: str = "21m00Tcm4TlvDq8ikWAM"
    elevenlabs_model: str = "eleven_multilingual_v2"
    tts_cache_dir: str = "media/tts-cache"
    #: Monthly character ceiling, checked before each call. 0 disables it.
    #: The free tier is 10,000/month; the default leaves headroom to notice a
    #: problem rather than sitting exactly on the cliff edge.
    elevenlabs_monthly_char_limit: int = 9000

    # LiveKit (self-hosted). The dev-mode container publishes devkey/secret,
    # which are in LiveKit's own documentation -- fine on a laptop, and an open
    # server anywhere reachable. Generate real values before deploying.
    livekit_url: str = ""
    livekit_api_key: str = ""
    livekit_api_secret: str = ""
    #: Public URL handed to the phone. The container talks to itself as
    #: ws://livekit:7880, but a device on the LAN cannot resolve that name, so
    #: the address the client is told is configured separately.
    livekit_public_url: str = ""

    @property
    def livekit_enabled(self) -> bool:
        return bool(
            self.livekit_url and self.livekit_api_key and self.livekit_api_secret
        )

    @property
    def livekit_client_url(self) -> str:
        return self.livekit_public_url or self.livekit_url

    # Dev/demo admin (seeded on SQLite startup so the admin panel is usable).
    seed_admin_email: str = "admin@ielts.local"
    seed_admin_password: str = "AdminPass123"

    # Rate limiting (in-memory per-process; back with Redis for multi-instance).
    rate_limit_enabled: bool = True
    rate_limit_login_per_min: int = 10
    rate_limit_register_per_min: int = 5
    rate_limit_ai_per_min: int = 20

    @property
    def environment(self) -> Environment:
        return Environment.parse(self.app_env)

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def docs_enabled(self) -> bool:
        """Interactive docs are a development tool.

        In production they hand an attacker a complete, accurate map of every
        endpoint and payload shape. The OpenAPI schema is still generated; it
        is simply not served.
        """
        return not self.environment.is_hardened

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")


@lru_cache
def get_settings() -> Settings:
    return Settings()
