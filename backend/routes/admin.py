"""Admin routes (RBAC-guarded)."""

from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from controllers.admin_users_controller import (
    AdminUserItem,
    AdminUsersController,
    AdminUserPage,
    UserUpdateRequest,
)
from controllers.admin_overview_controller import (
    AdminOverview,
    AdminOverviewController,
)
from controllers.ai_usage_controller import AIUsageController, AIUsageResponse
from controllers.pagination import DEFAULT_LIMIT
from db.session import get_db
from dependencies import require_roles
from models.user import User

router = APIRouter(prefix="/admin", tags=["admin"])

AdminUser = Annotated[User, Depends(require_roles("admin", "super_admin"))]
DbSession = Annotated[AsyncSession, Depends(get_db)]


@router.get("/overview", response_model=AdminOverview)
async def overview(current: AdminUser, session: DbSession) -> AdminOverview:
    return await AdminOverviewController.overview(session)


@router.get("/ai-usage", response_model=AIUsageResponse)
async def ai_usage(
    admin: AdminUser,
    session: DbSession,
    feature: Annotated[str | None, Query()] = None,
    date_from: Annotated[date | None, Query(alias="from")] = None,
    date_to: Annotated[date | None, Query(alias="to")] = None,
) -> AIUsageResponse:
    return await AIUsageController.summary(session, feature, date_from, date_to)


@router.get("/users", response_model=AdminUserPage)
async def list_users(
    admin: AdminUser,
    session: DbSession,
    search: Annotated[str | None, Query()] = None,
    cursor: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=50)] = DEFAULT_LIMIT,
) -> AdminUserPage:
    return await AdminUsersController.list_users(session, cursor, limit, search)


@router.patch("/users/{user_id}", response_model=AdminUserItem)
async def update_user(
    user_id: str,
    payload: UserUpdateRequest,
    admin: AdminUser,
    session: DbSession,
) -> AdminUserItem:
    return await AdminUsersController.update_user(session, admin, user_id, payload)
