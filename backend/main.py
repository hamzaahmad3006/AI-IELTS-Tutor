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
from db.session import init_models, seed_admin
from middleware import CorrelationIdMiddleware, register_exception_handlers
from routes import api_router

API_V1_PREFIX = "/v1"


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    # Dev convenience: auto-create tables + seed an admin when running on SQLite.
    # Production (PostgreSQL) uses Alembic migrations + a provisioned admin.
    if get_settings().is_sqlite:
        await init_models()
        await seed_admin()
    yield


app = FastAPI(
    title="AI IELTS Tutor API",
    version="1.0.0",
    description="Backend for the AI-powered IELTS preparation platform.",
    lifespan=lifespan,
)

# CORS (useful for local browser testing; RN native does not require it).
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(CorrelationIdMiddleware)

register_exception_handlers(app)

app.include_router(api_router, prefix=API_V1_PREFIX)


@app.get("/")
async def root() -> dict[str, str]:
    return {"service": "ai-ielts-tutor", "docs": "/docs", "api": API_V1_PREFIX}
