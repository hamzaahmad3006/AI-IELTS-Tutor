"""AI IELTS Tutor — FastAPI backend entry point.

Scaffold aligned with the SRS: layered routes -> controllers, correlation-id
and RFC 7807 error middleware, and a /v1 API prefix. Persistence (Supabase
PostgreSQL), JWT auth, the AI provider abstraction and the voice pipeline are
added in later milestones.

Run:  uvicorn main:app --reload --port 8000
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.config import get_settings
from core.logging import configure_logging
from db.session import init_models, seed_admin
from core.metrics import MetricsMiddleware
from core.environment import enforce
from middleware import CorrelationIdMiddleware, register_exception_handlers
from routes import api_router
from routes.health import router as health_router
from routes.media import router as media_router

API_V1_PREFIX = "/v1"


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    # Installed here rather than at import time so uvicorn has already set up
    # its own handlers and ours replace them cleanly.
    configure_logging(get_settings().log_level)

    # Dev convenience: auto-create tables + seed an admin when running on SQLite.
    # Production (PostgreSQL) uses Alembic migrations + a provisioned admin.
    if get_settings().is_sqlite:
        await init_models()
        await seed_admin()
    yield


_settings = get_settings()

# Refuses to start rather than warning. A warning in a log nobody reads is
# exactly how a service ends up serving production traffic on a signing key
# that is published in its own repository.
enforce(_settings)

app = FastAPI(
    title="AI IELTS Tutor API",
    version="1.0.0",
    description="Backend for the AI-powered IELTS preparation platform.",
    lifespan=lifespan,
    # Suppressed outside development: interactive docs hand an attacker an
    # accurate map of every endpoint and payload shape.
    docs_url="/docs" if _settings.docs_enabled else None,
    redoc_url="/redoc" if _settings.docs_enabled else None,
    openapi_url="/openapi.json" if _settings.docs_enabled else None,
)

# CORS (useful for local browser testing; RN native does not require it).
app.add_middleware(
    CORSMiddleware,
    allow_origins=_settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(CorrelationIdMiddleware)
# Outermost of the two, so the duration it records includes the time spent
# in every other middleware -- which is what a latency alert should fire on.
app.add_middleware(MetricsMiddleware)

register_exception_handlers(app)

app.include_router(health_router)  # root-level probes: /health, /ready
app.include_router(media_router)  # /media/... audio for the listening module
app.include_router(api_router, prefix=API_V1_PREFIX)


@app.get("/")
async def root() -> dict[str, str]:
    return {"service": "ai-ielts-tutor", "docs": "/docs", "api": API_V1_PREFIX}
