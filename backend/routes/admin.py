"""Admin routes (RBAC-guarded)."""

from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from controllers.ai_usage_controller import AIUsageController, AIUsageResponse
from db.session import get_db
from dependencies import require_roles
from models.user import User

router = APIRouter(prefix="/admin", tags=["admin"])

AdminUser = Annotated[User, Depends(require_roles("admin", "super_admin"))]
DbSession = Annotated[AsyncSession, Depends(get_db)]


@router.get("/ai-usage", response_model=AIUsageResponse)
async def ai_usage(
    admin: AdminUser,
    session: DbSession,
    feature: Annotated[str | None, Query()] = None,
    date_from: Annotated[date | None, Query(alias="from")] = None,
    date_to: Annotated[date | None, Query(alias="to")] = None,
) -> AIUsageResponse:
    return await AIUsageController.summary(session, feature, date_from, date_to)
