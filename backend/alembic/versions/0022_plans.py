"""per-user plan

Revision ID: 0022_plans
Revises: 0021_time_on_task
Create Date: 2026-08-10
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0022_plans"
down_revision: Union[str, None] = "0021_time_on_task"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Defaults to free, including for everyone who already exists. Defaulting
    # to a paid tier would hand out an allowance nobody bought, and defaulting
    # to NULL would mean every read has to decide what NULL means.
    op.add_column(
        "users",
        sa.Column("plan", sa.String(length=20), nullable=False, server_default="free"),
    )


def downgrade() -> None:
    op.drop_column("users", "plan")
