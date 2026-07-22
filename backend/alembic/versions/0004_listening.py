"""listening content + attempts (audio_clips, listening_questions, listening_attempts)

Revision ID: 0004_listening
Revises: 0003_reading
Create Date: 2026-07-22
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0004_listening"
down_revision: Union[str, None] = "0003_reading"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "audio_clips",
        sa.Column("id", sa.String(length=32), primary_key=True),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("object_key", sa.String(length=300), nullable=False),
        sa.Column("transcript", sa.Text(), nullable=False),
        sa.Column("duration_sec", sa.Integer(), server_default="0", nullable=False),
        sa.Column("exam_type", sa.String(length=20), server_default="academic", nullable=False),
        sa.Column("difficulty", sa.String(length=20), server_default="medium", nullable=False),
        sa.Column("accent", sa.String(length=40), nullable=True),
        sa.Column("source", sa.String(length=20), server_default="seed", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "listening_questions",
        sa.Column("id", sa.String(length=32), primary_key=True),
        sa.Column("audio_id", sa.String(length=32), nullable=False),
        sa.Column("order_index", sa.Integer(), server_default="0", nullable=False),
        sa.Column("type", sa.String(length=30), nullable=False),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("options", sa.JSON(), nullable=True),
        sa.Column("correct_answer", sa.JSON(), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=True),
        sa.Column("answer_timestamp", sa.String(length=20), nullable=True),
        sa.Column("difficulty", sa.String(length=20), server_default="medium", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["audio_id"], ["audio_clips.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_listening_questions_audio_id", "listening_questions", ["audio_id"])

    op.create_table(
        "listening_attempts",
        sa.Column("id", sa.String(length=32), primary_key=True),
        sa.Column("user_id", sa.String(length=32), nullable=False),
        sa.Column("audio_id", sa.String(length=32), nullable=True),
        sa.Column("answers", sa.JSON(), nullable=False),
        sa.Column("raw_score", sa.Integer(), server_default="0", nullable=False),
        sa.Column("total_questions", sa.Integer(), server_default="0", nullable=False),
        sa.Column("band", sa.Float(), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["audio_id"], ["audio_clips.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_listening_attempts_user_id", "listening_attempts", ["user_id"])


def downgrade() -> None:
    op.drop_table("listening_attempts")
    op.drop_index("ix_listening_questions_audio_id", table_name="listening_questions")
    op.drop_table("listening_questions")
    op.drop_table("audio_clips")
