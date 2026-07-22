"""speaking attempts table

Revision ID: 0005_speaking
Revises: 0004_listening
Create Date: 2026-07-22
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0005_speaking"
down_revision: Union[str, None] = "0004_listening"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "speaking_attempts",
        sa.Column("id", sa.String(length=32), primary_key=True),
        sa.Column("user_id", sa.String(length=32), nullable=False),
        sa.Column("part", sa.Integer(), nullable=True),
        sa.Column("transcript", sa.Text(), nullable=False),
        sa.Column("duration_sec", sa.Integer(), server_default="0", nullable=False),
        sa.Column("status", sa.String(length=20), server_default="scored", nullable=False),
        sa.Column("overall_band", sa.Float(), nullable=True),
        sa.Column("fluency_coherence", sa.Float(), nullable=True),
        sa.Column("lexical_resource", sa.Float(), nullable=True),
        sa.Column("grammatical_range", sa.Float(), nullable=True),
        sa.Column("pronunciation", sa.Float(), nullable=True),
        sa.Column("feedback_summary", sa.Text(), nullable=True),
        sa.Column("ai_provider", sa.String(length=32), nullable=True),
        sa.Column("ai_model", sa.String(length=64), nullable=True),
        sa.Column("total_tokens", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_speaking_attempts_user_id", "speaking_attempts", ["user_id"])


def downgrade() -> None:
    op.drop_table("speaking_attempts")
