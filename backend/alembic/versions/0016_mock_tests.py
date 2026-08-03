"""mock_tests table

Revision ID: 0016_mock_tests
Revises: 0015_study_plans
Create Date: 2026-08-02
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0016_mock_tests"
down_revision: Union[str, None] = "0015_study_plans"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "mock_tests",
        sa.Column("id", sa.String(length=32), primary_key=True),
        sa.Column("user_id", sa.String(length=32), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="in_progress", nullable=False),
        sa.Column("passage_id", sa.String(length=32), nullable=True),
        sa.Column("clip_id", sa.String(length=32), nullable=True),
        sa.Column("writing_prompt_id", sa.String(length=32), nullable=True),
        sa.Column("cue_card_id", sa.String(length=32), nullable=True),
        sa.Column("reading_band", sa.Float(), nullable=True),
        sa.Column("listening_band", sa.Float(), nullable=True),
        sa.Column("writing_band", sa.Float(), nullable=True),
        sa.Column("speaking_band", sa.Float(), nullable=True),
        sa.Column("overall_band", sa.Float(), nullable=True),
        sa.Column("readiness", sa.JSON(), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_mock_tests_user_id", "mock_tests", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_mock_tests_user_id", table_name="mock_tests")
    op.drop_table("mock_tests")
