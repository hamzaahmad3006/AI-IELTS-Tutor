"""writing attempts table

Revision ID: 0002_writing_attempts
Revises: 0001_initial
Create Date: 2026-07-22
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002_writing_attempts"
down_revision: Union[str, None] = "0001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "writing_attempts",
        sa.Column("id", sa.String(length=32), primary_key=True),
        sa.Column("user_id", sa.String(length=32), nullable=False),
        sa.Column("task_type", sa.Integer(), server_default="2", nullable=False),
        sa.Column("prompt_text", sa.Text(), nullable=True),
        sa.Column("essay_text", sa.Text(), nullable=False),
        sa.Column("word_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("status", sa.String(length=20), server_default="scored", nullable=False),
        sa.Column("overall_band", sa.Float(), nullable=True),
        sa.Column("task_response", sa.Float(), nullable=True),
        sa.Column("coherence_cohesion", sa.Float(), nullable=True),
        sa.Column("lexical_resource", sa.Float(), nullable=True),
        sa.Column("grammatical_range", sa.Float(), nullable=True),
        sa.Column("feedback_summary", sa.Text(), nullable=True),
        sa.Column("improved_essay", sa.Text(), nullable=True),
        sa.Column("ai_provider", sa.String(length=32), nullable=True),
        sa.Column("ai_model", sa.String(length=64), nullable=True),
        sa.Column("total_tokens", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_writing_attempts_user_id", "writing_attempts", ["user_id"])


def downgrade() -> None:
    op.drop_table("writing_attempts")
