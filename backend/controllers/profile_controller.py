"""Profile & onboarding controller: schemas + database-backed logic."""

from __future__ import annotations

from datetime import date

from fastapi import HTTPException, status
from pydantic import Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.profile import LearnerProfile
from models.user import User

from .base import CamelModel

ExamType = str  # 'academic' | 'general'
Level = str  # 'beginner' | 'intermediate' | 'advanced'


class ModuleBaselines(CamelModel):
    speaking: float | None = None
    writing: float | None = None
    reading: float | None = None
    listening: float | None = None


class OnboardingRequest(CamelModel):
    exam_type: ExamType = "academic"
    self_level: Level = "beginner"
    target_band: float = Field(ge=0, le=9)
    exam_date: date | None = None
    daily_minutes: int = Field(default=30, gt=0, le=1440)
    consent_voice: bool = False
    consent_ai: bool = False


class ProfileUpdateRequest(CamelModel):
    exam_type: ExamType | None = None
    self_level: Level | None = None
    target_band: float | None = Field(default=None, ge=0, le=9)
    exam_date: date | None = None
    daily_minutes: int | None = Field(default=None, gt=0, le=1440)
    consent_voice: bool | None = None
    consent_ai: bool | None = None


class ProfileResponse(CamelModel):
    user_id: str
    exam_type: ExamType
    self_level: Level
    cefr_level: str | None
    target_band: float
    exam_date: date | None
    daily_minutes: int
    baselines: ModuleBaselines
    consent_voice: bool
    consent_ai: bool


def _to_response(profile: LearnerProfile) -> ProfileResponse:
    return ProfileResponse(
        user_id=profile.user_id,
        exam_type=profile.exam_type,
        self_level=profile.self_level,
        cefr_level=profile.cefr_level,
        target_band=profile.target_band,
        exam_date=profile.exam_date,
        daily_minutes=profile.daily_minutes,
        baselines=ModuleBaselines(
            speaking=profile.baseline_speaking,
            writing=profile.baseline_writing,
            reading=profile.baseline_reading,
            listening=profile.baseline_listening,
        ),
        consent_voice=profile.consent_voice,
        consent_ai=profile.consent_ai,
    )


class ProfileController:
    @staticmethod
    async def _get(session: AsyncSession, user_id: str) -> LearnerProfile | None:
        return await session.scalar(
            select(LearnerProfile).where(LearnerProfile.user_id == user_id)
        )

    @classmethod
    async def submit_onboarding(
        cls, session: AsyncSession, user: User, payload: OnboardingRequest
    ) -> ProfileResponse:
        profile = await cls._get(session, user.id)
        if profile is None:
            profile = LearnerProfile(user_id=user.id, target_band=payload.target_band)
            session.add(profile)
        profile.exam_type = payload.exam_type
        profile.self_level = payload.self_level
        profile.target_band = payload.target_band
        profile.exam_date = payload.exam_date
        profile.daily_minutes = payload.daily_minutes
        profile.consent_voice = payload.consent_voice
        profile.consent_ai = payload.consent_ai
        await session.flush()
        return _to_response(profile)

    @classmethod
    async def get_profile(
        cls, session: AsyncSession, user: User
    ) -> ProfileResponse:
        profile = await cls._get(session, user.id)
        if profile is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Profile not found. Complete onboarding first.",
            )
        return _to_response(profile)

    @classmethod
    async def update_profile(
        cls, session: AsyncSession, user: User, payload: ProfileUpdateRequest
    ) -> ProfileResponse:
        profile = await cls._get(session, user.id)
        if profile is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found"
            )
        data = payload.model_dump(exclude_unset=True)
        for field, value in data.items():
            setattr(profile, field, value)
        await session.flush()
        return _to_response(profile)
