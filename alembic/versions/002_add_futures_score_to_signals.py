"""add futures_score to signals

Revision ID: 002
Revises: 001
Create Date: 2026-04-24

"""
from alembic import op
import sqlalchemy as sa

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "signals",
        sa.Column("futures_score", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("signals", "futures_score")
