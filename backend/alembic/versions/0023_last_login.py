"""last login timestamp

Revision ID: 0023_last_login
Revises: 0022_plans
Create Date: 2026-08-10

SRS section 15 also specifies `deleted_at` on users, for soft deletion. That is
deliberately not implemented.

Account deletion here is a real deletion: privacy_controller removes the rows
and anonymises the usage records. A soft-deleted account still holds the
person's email, their essays and their transcripts, which is the opposite of
what someone asking to be deleted is asking for. Keeping both would mean two
deletion paths where the weaker one is the default, and the weaker one is the
one that gets used by accident.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0023_last_login"
down_revision: Union[str, None] = "0022_plans"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Nullable: existing accounts genuinely have no recorded last login, and
    # backfilling created_at would assert something untrue about when they
    # were last seen -- which is exactly what this column is read for.
    op.add_column(
        "users", sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("users", "last_login_at")
