"""speaking_questions table (Part 1 and Part 3 banks)

Revision ID: 0013_speaking_questions
Revises: 0012_grammar_lessons
Create Date: 2026-08-02
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0013_speaking_questions"
down_revision: Union[str, None] = "0012_grammar_lessons"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "speaking_questions",
        sa.Column("id", sa.String(length=32), primary_key=True),
        sa.Column("part", sa.Integer(), nullable=False),
        sa.Column("topic", sa.String(length=120), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("order_index", sa.Integer(), server_default="1", nullable=False),
        sa.Column("difficulty", sa.String(length=20), server_default="medium", nullable=False),
        sa.Column("source", sa.String(length=20), server_default="seed", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_speaking_questions_part", "speaking_questions", ["part"])
    op.create_index("ix_speaking_questions_topic", "speaking_questions", ["topic"])


def downgrade() -> None:
    op.drop_index("ix_speaking_questions_topic", table_name="speaking_questions")
    op.drop_index("ix_speaking_questions_part", table_name="speaking_questions")
    op.drop_table("speaking_questions")
