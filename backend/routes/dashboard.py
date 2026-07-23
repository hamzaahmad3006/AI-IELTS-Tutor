"""Dashboard route: real Home overview composed from stored data."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from controllers.dashboard_controller import DashboardController, DashboardData
from db.session import get_db
from dependencies import get_current_user
from models.user import User

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/overview", response_model=DashboardData)
async def overview(
    current: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> DashboardData:
    return await DashboardController.overview(session, current)
