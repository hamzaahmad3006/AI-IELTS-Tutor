"""Routes package: aggregates all API routers under the /v1 prefix."""

from fastapi import APIRouter

from . import (
    admin,
    admin_content,
    analytics,
    auth,
    dashboard,
    health,
    listening,
    onboarding,
    profile,
    reading,
    speaking,
    writing,
)

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(onboarding.router)
api_router.include_router(profile.router)
api_router.include_router(writing.router)
api_router.include_router(reading.router)
api_router.include_router(listening.router)
api_router.include_router(speaking.router)
api_router.include_router(analytics.router)
api_router.include_router(admin.router)
api_router.include_router(admin_content.router)
api_router.include_router(dashboard.router)

__all__ = ["api_router"]
