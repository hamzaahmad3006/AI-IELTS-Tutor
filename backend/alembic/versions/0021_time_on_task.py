"""time on task for every module

Revision ID: 0021_time_on_task
Revises: 0020_job_runs
Create Date: 2026-08-06
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0021_time_on_task"
down_revision: Union[str, None] = "0020_job_runs"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Speaking already had one, because a spoken answer has an obvious duration.
_TABLES = ("writing_attempts", "reading_attempts", "listening_attempts")


def upgrade() -> None:
    for table in _TABLES:
        # Zero rather than NULL: existing rows genuinely have no measurement,
        # and "0 minutes" is the honest total for work whose duration nobody
        # recorded. A NULL would have to be excluded from every sum, and the
        # first place that forgot would report a wrong number confidently.
        op.add_column(
            table,
            sa.Column(
                "duration_sec", sa.Integer(), nullable=False, server_default="0"
            ),
        )


def downgrade() -> None:
    for table in reversed(_TABLES):
        op.drop_column(table, "duration_sec")
