"""Dashboard/analytics routes."""

from __future__ import annotations

from fastapi import APIRouter

from controllers.dashboard_controller import DashboardController, DashboardData

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/overview", response_model=DashboardData)
async def overview() -> DashboardData:
    # TODO: resolve user_id from the JWT once auth is wired.
    return DashboardController.overview(user_id="usr_1")
