"""Analytics routes: per-module progress and band prediction."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from controllers.analytics_controller import (
    AnalyticsController,
    PredictionResponse,
    ProgressResponse,
    TrendResponse,
)
from db.session import get_db
from dependencies import get_current_user
from models.user import User

router = APIRouter(prefix="/analytics", tags=["analytics"])

DbSession = Annotated[AsyncSession, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]


@router.get("/progress", response_model=ProgressResponse)
async def progress(current: CurrentUser, session: DbSession) -> ProgressResponse:
    return await AnalyticsController.progress(session, current)


@router.get("/trend", response_model=TrendResponse)
async def trend(current: CurrentUser, session: DbSession) -> TrendResponse:
    return await AnalyticsController.trend(session, current)


@router.get("/prediction", response_model=PredictionResponse)
async def prediction(current: CurrentUser, session: DbSession) -> PredictionResponse:
    return await AnalyticsController.prediction(session, current)
