"""Privacy controller: full data export and account deletion.

Both operations are irreversible from the learner's point of view and are the
kind of thing a regulator asks about, so each writes an `AuditLog` row. Audit
rows deliberately outlive the account: `audit_logs.actor_id` carries no foreign
key, so the record that a deletion happened survives the deletion itself.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from models.ai_interaction import AIInteraction
from models.attempt import WritingAttempt
from models.audit import AuditLog
from models.listening import ListeningAttempt
from models.profile import LearnerProfile
from models.reading import ReadingAttempt
from models.speaking import SpeakingAttempt
from models.user import RefreshToken, User
from models.vocabulary import VocabReview
from models.interview import InterviewSession
from models.mock_test import MockTest
from models.plan import PlanTask, StudyPlan
from models.weakness import Weakness

from .base import CamelModel

logger = logging.getLogger("api.privacy")


class DeleteAccountResponse(CamelModel):
    deleted: bool
    #: Rows removed per table, so the caller can see the deletion really landed.
    removed: dict[str, int]


def _row_to_dict(row: object) -> dict[str, Any]:
    """Serialise an ORM row using its mapped columns only."""
    mapper = getattr(type(row), "__mapper__", None)
    if mapper is None:
        return {}
    return {
        column.key: getattr(row, column.key) for column in mapper.column_attrs
    }


#: Every table keyed by user_id.
#:
#: This list is the definition of "everything we hold about you" for both the
#: export and the deletion, so a table missing from it is silently excluded
#: from both -- exported data that is incomplete, and deleted data that is not
#: deleted. Three tables added after this controller was written (study plans,
#: mock tests, interview sessions) were exactly that, and interview sessions
#: hold spoken transcripts, which is about as personal as this app gets.
#:
#: There is a test that reflects over the ORM metadata and fails when a model
#: with a user_id column is not listed here, so the next table added cannot be
#: forgotten the same way.
_OWNED = (
    ("profile", LearnerProfile),
    ("writingAttempts", WritingAttempt),
    ("speakingAttempts", SpeakingAttempt),
    ("readingAttempts", ReadingAttempt),
    ("listeningAttempts", ListeningAttempt),
    ("weaknesses", Weakness),
    ("vocabReviews", VocabReview),
    ("studyPlans", StudyPlan),
    ("mockTests", MockTest),
    ("interviewSessions", InterviewSession),
)


class PrivacyController:
    @staticmethod
    async def export(session: AsyncSession, user: User) -> dict[str, Any]:
        """Everything held about this learner, as plain JSON."""
        export: dict[str, Any] = {
            "exportedAt": datetime.now(tz=timezone.utc).isoformat(),
            "account": {
                "id": user.id,
                "email": user.email,
                "fullName": user.full_name,
                "role": user.role,
                "emailVerified": user.email_verified,
                "createdAt": user.created_at,
            },
        }

        for key, model in _OWNED:
            rows = (
                await session.execute(
                    select(model).where(model.user_id == user.id)
                )
            ).scalars().all()
            serialised = [_row_to_dict(row) for row in rows]
            # The profile is one-per-user; exporting it as a list would be
            # technically correct and practically annoying.
            export[key] = (
                (serialised[0] if serialised else None)
                if key == "profile"
                else serialised
            )

        # Plan tasks hang off plans rather than the user, so the loop above
        # misses them -- and they are the actual study content, not metadata.
        plan_tasks = await session.scalars(
            select(PlanTask).where(
                PlanTask.plan_id.in_(
                    select(StudyPlan.id).where(StudyPlan.user_id == user.id)
                )
            )
        )
        export["planTasks"] = [_row_to_dict(row) for row in plan_tasks]

        # Credentials are never exported: a password hash is not useful to the
        # learner and re-exposing it widens the blast radius of a leaked export.
        logger.info(
            "data export produced",
            extra={"userId": user.id, "tables": len(_OWNED)},
        )
        session.add(
            AuditLog(
                actor_id=user.id,
                action="privacy.export",
                entity_type="user",
                entity_id=user.id,
            )
        )
        return export

    @staticmethod
    async def delete_account(
        session: AsyncSession, user: User
    ) -> DeleteAccountResponse:
        """Erase the learner and everything belonging to them."""
        user_id = user.id
        removed: dict[str, int] = {}

        # Plan tasks are keyed by plan_id, not user_id, so they are not caught
        # by the loop below. Removed first, while their parent plans still
        # exist to identify them -- afterwards there is nothing left to join on
        # and the rows are orphaned rather than deleted.
        result = await session.execute(
            delete(PlanTask).where(
                PlanTask.plan_id.in_(
                    select(StudyPlan.id).where(StudyPlan.user_id == user_id)
                )
            )
        )
        removed["planTasks"] = result.rowcount or 0

        for key, model in _OWNED:
            result = await session.execute(
                delete(model).where(model.user_id == user_id)
            )
            removed[key] = result.rowcount or 0

        result = await session.execute(
            delete(RefreshToken).where(RefreshToken.user_id == user_id)
        )
        removed["refreshTokens"] = result.rowcount or 0

        # AI usage rows are billing/telemetry, not learner content, and the
        # column is nullable by design. Anonymising keeps aggregate usage
        # honest while severing the link to a deleted person — deleting them
        # instead would silently rewrite historical cost reporting.
        result = await session.execute(
            update(AIInteraction)
            .where(AIInteraction.user_id == user_id)
            .values(user_id=None)
        )
        removed["aiInteractionsAnonymised"] = result.rowcount or 0

        result = await session.execute(delete(User).where(User.id == user_id))
        removed["account"] = result.rowcount or 0

        # Written after the delete so the audit trail records a completed
        # action. actor_id has no FK, so this row survives the account.
        session.add(
            AuditLog(
                actor_id=user_id,
                action="privacy.delete_account",
                entity_type="user",
                entity_id=user_id,
                audit_metadata=removed,
            )
        )
        logger.info(
            "account deleted", extra={"userId": user_id, "removed": removed}
        )
        return DeleteAccountResponse(deleted=True, removed=removed)
