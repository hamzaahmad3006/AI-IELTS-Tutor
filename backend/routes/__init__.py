"""Routes package: aggregates all API routers under the /v1 prefix."""

from fastapi import APIRouter

from . import (
    admin,
    admin_content,
    analytics,
    auth,
    dashboard,
    diagnostic,
    grammar,
    listening,
    me,
    onboarding,
    profile,
    reading,
    speaking,
    vocabulary,
    writing,
)

# NOTE: health/readiness probes are mounted at the app root (see main.py), not
# under the /v1 API prefix, so orchestrators can reach /health and /ready.
api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(onboarding.router)
api_router.include_router(profile.router)
api_router.include_router(me.router)
api_router.include_router(writing.router)
api_router.include_router(reading.router)
api_router.include_router(listening.router)
api_router.include_router(speaking.router)
api_router.include_router(vocabulary.router)
api_router.include_router(grammar.router)
api_router.include_router(diagnostic.router)
api_router.include_router(analytics.router)
api_router.include_router(admin.router)
api_router.include_router(admin_content.router)
api_router.include_router(dashboard.router)

__all__ = ["api_router"]
