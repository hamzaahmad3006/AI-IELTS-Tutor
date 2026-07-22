"""Routes package: aggregates all API routers under the /v1 prefix."""

from fastapi import APIRouter

from . import auth, dashboard, health, onboarding, profile, writing

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(onboarding.router)
api_router.include_router(profile.router)
api_router.include_router(writing.router)
api_router.include_router(dashboard.router)

__all__ = ["api_router"]
