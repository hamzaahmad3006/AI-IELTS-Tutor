"""prompt id/version on ai_interactions

Revision ID: 0017_prompt_version
Revises: 0016_mock_tests
Create Date: 2026-08-04
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0017_prompt_version"
down_revision: Union[str, None] = "0016_mock_tests"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Nullable rather than backfilled: rows written before the registry existed
    # genuinely have no known prompt version, and inventing one would assert
    # something untrue about how those scores were produced.
    op.add_column(
        "ai_interactions",
        sa.Column("prompt_id", sa.String(length=60), nullable=True),
    )
    op.add_column(
        "ai_interactions",
        sa.Column("prompt_version", sa.String(length=20), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("ai_interactions", "prompt_version")
    op.drop_column("ai_interactions", "prompt_id")
