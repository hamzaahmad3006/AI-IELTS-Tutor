"""job run bookkeeping (and the scheduler's lock)

Revision ID: 0020_job_runs
Revises: 0019_interview_sessions
Create Date: 2026-08-06
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0020_job_runs"
down_revision: Union[str, None] = "0019_interview_sessions"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "job_runs",
        # The job name is the key: exactly one row per job, and a surrogate id
        # would allow two -- which would quietly defeat the lock.
        sa.Column("name", sa.String(length=60), primary_key=True),
        sa.Column("last_started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_status", sa.String(length=16), nullable=True),
        sa.Column("last_detail", sa.Text(), nullable=True),
        sa.Column(
            "consecutive_failures", sa.Integer(), nullable=False, server_default="0"
        ),
    )


def downgrade() -> None:
    op.drop_table("job_runs")
