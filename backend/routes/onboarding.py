"""Onboarding routes."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from controllers.profile_controller import (
    OnboardingRequest,
    ProfileController,
    ProfileResponse,
)
from db.session import get_db
from dependencies import get_current_user
from models.user import User

router = APIRouter(prefix="/onboarding", tags=["onboarding"])


@router.post("", response_model=ProfileResponse, status_code=status.HTTP_201_CREATED)
async def submit_onboarding(
    payload: OnboardingRequest,
    current: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ProfileResponse:
    return await ProfileController.submit_onboarding(session, current, payload)
