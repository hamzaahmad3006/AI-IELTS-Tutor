"""study_plans and plan_tasks tables

Revision ID: 0015_study_plans
Revises: 0014_attempt_issues
Create Date: 2026-08-02
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0015_study_plans"
down_revision: Union[str, None] = "0014_attempt_issues"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "study_plans",
        sa.Column("id", sa.String(length=32), primary_key=True),
        sa.Column("user_id", sa.String(length=32), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("target_band", sa.Float(), nullable=False),
        sa.Column("exam_date", sa.Date(), nullable=True),
        sa.Column("daily_minutes", sa.Integer(), server_default="30", nullable=False),
        sa.Column("weeks", sa.Integer(), server_default="4", nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_study_plans_user_id", "study_plans", ["user_id"])

    op.create_table(
        "plan_tasks",
        sa.Column("id", sa.String(length=32), primary_key=True),
        sa.Column("plan_id", sa.String(length=32), sa.ForeignKey("study_plans.id", ondelete="CASCADE"), nullable=False),
        sa.Column("week", sa.Integer(), server_default="1", nullable=False),
        sa.Column("module", sa.String(length=20), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("detail", sa.Text(), nullable=False),
        sa.Column("minutes", sa.Integer(), server_default="20", nullable=False),
        sa.Column("priority", sa.Float(), server_default="0", nullable=False),
        sa.Column("is_done", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_plan_tasks_plan_id", "plan_tasks", ["plan_id"])


def downgrade() -> None:
    op.drop_index("ix_plan_tasks_plan_id", table_name="plan_tasks")
    op.drop_table("plan_tasks")
    op.drop_index("ix_study_plans_user_id", table_name="study_plans")
    op.drop_table("study_plans")
