"""AI IELTS Tutor — FastAPI backend entry point.

Scaffold aligned with the SRS: layered routes -> controllers, correlation-id
and RFC 7807 error middleware, and a /v1 API prefix. Persistence (Supabase
PostgreSQL), JWT auth, the AI provider abstraction and the voice pipeline are
added in later milestones.

Run:  uvicorn main:app --reload --port 8000
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from middleware import CorrelationIdMiddleware, register_exception_handlers
from routes import api_router

API_V1_PREFIX = "/v1"

app = FastAPI(
    title="AI IELTS Tutor API",
    version="1.0.0",
    description="Backend for the AI-powered IELTS preparation platform.",
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
