"""Learner self-service routes (`/me`)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from controllers.weakness_controller import WeaknessListResponse, WeaknessService
from db.session import get_db
from dependencies import get_current_user
from models.user import User

router = APIRouter(prefix="/me", tags=["me"])

DbSession = Annotated[AsyncSession, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]


@router.get("/weaknesses", response_model=WeaknessListResponse)
async def weaknesses(
    current: CurrentUser,
    session: DbSession,
    include_resolved: Annotated[bool, Query(alias="includeResolved")] = False,
) -> WeaknessListResponse:
    return await WeaknessService.list_for_user(session, current.id, include_resolved)
