"""Analytics controller: per-module progress + band prediction from attempts."""

from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.predictor import confidence, project, round_half, velocity_per_week
from models.attempt import WritingAttempt
from models.listening import ListeningAttempt
from models.profile import LearnerProfile
from models.reading import ReadingAttempt
from models.speaking import SpeakingAttempt
from models.user import User

from .base import CamelModel

MODULES = ("speaking", "writing", "reading", "listening")

# (model, band_column, optional status filter)
_SOURCES = {
    "writing": (WritingAttempt, WritingAttempt.overall_band, "scored"),
    "speaking": (SpeakingAttempt, SpeakingAttempt.overall_band, "scored"),
    "reading": (ReadingAttempt, ReadingAttempt.band, None),
    "listening": (ListeningAttempt, ListeningAttempt.band, None),
}


# ---------- Schemas ----------
class ModuleProgress(CamelModel):
    module: str
    attempts: int
    current_band: float | None
    average_band: float | None


class ProgressResponse(CamelModel):
    modules: list[ModuleProgress]
    overall_band: float | None
    total_attempts: int


class TrendPoint(CamelModel):
    at: datetime
    band: float


class ModuleTrend(CamelModel):
    module: str
    points: list[TrendPoint]


class TrendResponse(CamelModel):
    modules: list[ModuleTrend]
    # Running overall band after each attempt: the mean of the latest band in
    # every module that has one, recomputed at each point in time. This is what
    # a learner watches move, so it is derived server-side rather than leaving
    # each client to reinvent it.
    overall: list[TrendPoint]


class PredictionModules(CamelModel):
    speaking: float | None
    writing: float | None
    reading: float | None
    listening: float | None


class PredictionResponse(CamelModel):
    predicted_overall: float | None
    confidence: float
    horizon_date: date | None
    modules: PredictionModules
    velocity_per_week: PredictionModules
    note: str


# ---------- Data access ----------
async def _module_points(
    session: AsyncSession, user_id: str, module: str
) -> list[tuple[datetime, float]]:
    model, band_col, status_filter = _SOURCES[module]
    query = select(model.created_at, band_col).where(model.user_id == user_id)
    if status_filter is not None:
        query = query.where(model.status == status_filter)
    query = query.where(band_col.is_not(None)).order_by(model.created_at)
    rows = (await session.execute(query)).all()
    points: list[tuple[datetime, float]] = []
    for created_at, band in rows:
        ts = created_at if created_at.tzinfo else created_at.replace(tzinfo=timezone.utc)
        points.append((ts, float(band)))
    return points


class AnalyticsController:
    @staticmethod
    async def progress(session: AsyncSession, user: User) -> ProgressResponse:
        modules: list[ModuleProgress] = []
        currents: list[float] = []
        total = 0
        for module in MODULES:
            points = await _module_points(session, user.id, module)
            bands = [b for _, b in points]
            total += len(bands)
            current = bands[-1] if bands else None
            avg = round_half(sum(bands) / len(bands)) if bands else None
            if current is not None:
                currents.append(current)
            modules.append(
                ModuleProgress(
                    module=module,
                    attempts=len(bands),
                    current_band=current,
                    average_band=avg,
                )
            )
        overall = round_half(sum(currents) / len(currents)) if currents else None
        return ProgressResponse(
            modules=modules, overall_band=overall, total_attempts=total
        )

    @staticmethod
    async def trend(session: AsyncSession, user: User) -> TrendResponse:
        """Per-module band series plus the running overall, oldest first."""
        module_trends: list[ModuleTrend] = []
        # (timestamp, module, band) across every module, to replay in order.
        merged: list[tuple[datetime, str, float]] = []

        for module in MODULES:
            points = await _module_points(session, user.id, module)
            module_trends.append(
                ModuleTrend(
                    module=module,
                    points=[TrendPoint(at=ts, band=band) for ts, band in points],
                )
            )
            merged.extend((ts, module, band) for ts, band in points)

        merged.sort(key=lambda row: row[0])

        overall: list[TrendPoint] = []
        latest: dict[str, float] = {}
        for ts, module, band in merged:
            latest[module] = band
            overall.append(
                TrendPoint(at=ts, band=round_half(sum(latest.values()) / len(latest)))
            )

        return TrendResponse(modules=module_trends, overall=overall)

    @staticmethod
    async def prediction(session: AsyncSession, user: User) -> PredictionResponse:
        profile = await session.scalar(
            select(LearnerProfile).where(LearnerProfile.user_id == user.id)
        )
        horizon_date = profile.exam_date if profile else None
        if horizon_date:
            weeks_ahead = max(1.0, (horizon_date - date.today()).days / 7.0)
        else:
            weeks_ahead = 4.0

        predicted: dict[str, float | None] = {}
        velocities: dict[str, float | None] = {}
        predicted_values: list[float] = []
        all_bands: list[float] = []

        for module in MODULES:
            points = await _module_points(session, user.id, module)
            bands = [b for _, b in points]
            all_bands.extend(bands)
            if not bands:
                predicted[module] = None
                velocities[module] = None
                continue
            v = velocity_per_week(points)
            proj = project(bands[-1], v, weeks_ahead)
            predicted[module] = proj
            velocities[module] = round(v, 3)
            predicted_values.append(proj)

        predicted_overall = (
            round_half(sum(predicted_values) / len(predicted_values))
            if predicted_values
            else None
        )
        note = (
            "Estimate based on your recent trajectory; not an official IELTS result."
        )
        return PredictionResponse(
            predicted_overall=predicted_overall,
            confidence=confidence(all_bands),
            horizon_date=horizon_date,
            modules=PredictionModules(**predicted),
            velocity_per_week=PredictionModules(**velocities),
            note=note,
        )
