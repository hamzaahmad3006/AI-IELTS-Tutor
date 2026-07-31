"""Learner self-service routes (`/me`)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from controllers.adaptive_controller import (
    AdaptiveController,
    DifficultyResponse,
    RecommendationsResponse,
)
from controllers.privacy_controller import (
    DeleteAccountResponse,
    PrivacyController,
)
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


@router.get("/adaptive-difficulty", response_model=DifficultyResponse)
async def adaptive_difficulty(
    current: CurrentUser, session: DbSession
) -> DifficultyResponse:
    return await AdaptiveController.difficulty_overview(session, current)


@router.get("/recommendations", response_model=RecommendationsResponse)
async def recommendations(
    current: CurrentUser, session: DbSession
) -> RecommendationsResponse:
    return await AdaptiveController.recommendations(session, current)


@router.get("/export")
async def export_data(
    current: CurrentUser, session: DbSession
) -> dict[str, object]:
    """Everything held about the signed-in learner, as JSON."""
    return await PrivacyController.export(session, current)


@router.delete("", response_model=DeleteAccountResponse)
async def delete_account(
    current: CurrentUser, session: DbSession
) -> DeleteAccountResponse:
    """Irreversibly erase the signed-in learner and all their data."""
    return await PrivacyController.delete_account(session, current)
