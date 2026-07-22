"""reading content + attempts (passages, questions, reading_attempts)

Revision ID: 0003_reading
Revises: 0002_writing_attempts
Create Date: 2026-07-22
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003_reading"
down_revision: Union[str, None] = "0002_writing_attempts"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "passages",
        sa.Column("id", sa.String(length=32), primary_key=True),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("exam_type", sa.String(length=20), server_default="academic", nullable=False),
        sa.Column("difficulty", sa.String(length=20), server_default="medium", nullable=False),
        sa.Column("topic", sa.String(length=120), nullable=True),
        sa.Column("word_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("source", sa.String(length=20), server_default="seed", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "questions",
        sa.Column("id", sa.String(length=32), primary_key=True),
        sa.Column("passage_id", sa.String(length=32), nullable=False),
        sa.Column("order_index", sa.Integer(), server_default="0", nullable=False),
        sa.Column("type", sa.String(length=30), nullable=False),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("options", sa.JSON(), nullable=True),
        sa.Column("correct_answer", sa.JSON(), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=True),
        sa.Column("difficulty", sa.String(length=20), server_default="medium", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["passage_id"], ["passages.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_questions_passage_id", "questions", ["passage_id"])

    op.create_table(
        "reading_attempts",
        sa.Column("id", sa.String(length=32), primary_key=True),
        sa.Column("user_id", sa.String(length=32), nullable=False),
        sa.Column("passage_id", sa.String(length=32), nullable=True),
        sa.Column("answers", sa.JSON(), nullable=False),
        sa.Column("raw_score", sa.Integer(), server_default="0", nullable=False),
        sa.Column("total_questions", sa.Integer(), server_default="0", nullable=False),
        sa.Column("band", sa.Float(), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["passage_id"], ["passages.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_reading_attempts_user_id", "reading_attempts", ["user_id"])


def downgrade() -> None:
    op.drop_table("reading_attempts")
    op.drop_index("ix_questions_passage_id", table_name="questions")
    op.drop_table("questions")
    op.drop_table("passages")
