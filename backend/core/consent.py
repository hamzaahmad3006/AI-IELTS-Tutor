"""Consent enforcement.

Consent was collected at onboarding and stored on the profile, and then nothing
ever read it. A checkbox that changes no behaviour is not consent, it is
decoration -- and it is worse than no checkbox at all, because it tells the
learner a decision was respected when it was not.

Two separate permissions, because they cover genuinely different exposures:

* **AI** — the learner's writing or speech is sent to a third-party model,
  which is a disclosure to someone outside this system.
* **Voice** — their microphone is recorded and the audio leaves the device.
  Someone can be perfectly happy having an essay scored and unwilling to be
  recorded, and collapsing the two into one flag denies them that.

A missing profile counts as *not* consented. The alternative -- treating "never
asked" as "agreed" -- means anyone who skips onboarding gets the permissive
path, which turns the whole mechanism into a formality. Onboarding is one screen
and the client already requires it.
"""

from __future__ import annotations

from typing import Literal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.errors import AppError
from models.profile import LearnerProfile

ConsentKind = Literal["ai", "voice"]


class ConsentRequiredError(AppError):
    """The learner has not agreed to this, or has not been asked yet.

    403 rather than 401: the caller is authenticated and known. Nothing is
    wrong with their credentials, they simply have not permitted this.
    """

    status = 403
    code = "consent_required"
    title = "Consent required"


_MESSAGES: dict[ConsentKind, str] = {
    "ai": (
        "AI feedback is turned off for your account. Turn it on in your "
        "profile to have your work scored."
    ),
    "voice": (
        "Voice recording is turned off for your account. Turn it on in your "
        "profile to answer out loud, or type your answers instead."
    ),
}


async def has_consent(
    session: AsyncSession, user_id: str, kind: ConsentKind
) -> bool:
    profile = await session.scalar(
        select(LearnerProfile).where(LearnerProfile.user_id == user_id)
    )
    if profile is None:
        return False
    return bool(profile.consent_ai if kind == "ai" else profile.consent_voice)


async def require_consent(
    session: AsyncSession, user_id: str, kind: ConsentKind
) -> None:
    """Raise unless the learner has agreed to this.

    Called at the point of use rather than checked once at login, so revoking
    consent in the profile takes effect on the next request instead of at the
    next sign-in.
    """
    if not await has_consent(session, user_id, kind):
        raise ConsentRequiredError(_MESSAGES[kind])
