"""interview sessions (spoken speaking test)

Revision ID: 0019_interview_sessions
Revises: 0018_indexes_retention
Create Date: 2026-08-05
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0019_interview_sessions"
down_revision: Union[str, None] = "0018_indexes_retention"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_JSON = sa.JSON().with_variant(JSONB(), "postgresql")


def upgrade() -> None:
    op.create_table(
        "interview_sessions",
        sa.Column("id", sa.String(length=32), primary_key=True),
        sa.Column(
            "user_id",
            sa.String(length=32),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("phase", sa.String(length=24), nullable=False, server_default="greeting"),
        # The script is frozen at creation so a resumed session continues the
        # same exam rather than quietly becoming a different one.
        sa.Column("script", _JSON, nullable=False),
        sa.Column("turns", _JSON, nullable=False),
        sa.Column("cursor", sa.Integer(), nullable=False, server_default="0"),
        # Records how the transcript was produced -- on-device recognition and a
        # server-side model fail differently, and a bad score needs to be
        # traceable to a bad transcription rather than blamed on the scorer.
        sa.Column(
            "transcript_source",
            sa.String(length=30),
            nullable=False,
            server_default="unknown",
        ),
        sa.Column("speaking_attempt_id", sa.String(length=32), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )
    op.create_index("ix_interview_sessions_user_id", "interview_sessions", ["user_id"])
    op.create_index(
        "ix_interview_sessions_user_created",
        "interview_sessions",
        ["user_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_interview_sessions_user_created", table_name="interview_sessions")
    op.drop_index("ix_interview_sessions_user_id", table_name="interview_sessions")
    op.drop_table("interview_sessions")
