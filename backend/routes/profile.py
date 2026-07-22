"""Profile routes."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from controllers.profile_controller import (
    ProfileController,
    ProfileResponse,
    ProfileUpdateRequest,
)
from db.session import get_db
from dependencies import get_current_user
from models.user import User

router = APIRouter(prefix="/profile", tags=["profile"])

DbSession = Annotated[AsyncSession, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]


@router.get("", response_model=ProfileResponse)
async def get_profile(current: CurrentUser, session: DbSession) -> ProfileResponse:
    return await ProfileController.get_profile(session, current)


@router.patch("", response_model=ProfileResponse)
async def update_profile(
    payload: ProfileUpdateRequest, current: CurrentUser, session: DbSession
) -> ProfileResponse:
    return await ProfileController.update_profile(session, current, payload)
