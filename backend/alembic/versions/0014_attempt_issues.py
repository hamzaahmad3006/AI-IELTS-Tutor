"""issues column on speaking_attempts (resolved highlight spans)

Revision ID: 0014_attempt_issues
Revises: 0013_speaking_questions
Create Date: 2026-08-02
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0014_attempt_issues"
down_revision: Union[str, None] = "0013_speaking_questions"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Spans are stored resolved rather than recomputed on read: the transcript
    # never changes after scoring, so re-running the match on every fetch would
    # be wasted work, and storing them keeps a record of what the model actually
    # flagged at the time.
    op.add_column(
        "speaking_attempts",
        sa.Column("issues", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("speaking_attempts", "issues")
