"""add updated_at to signals

Revision ID: 001
Revises:
Create Date: 2026-04-24

"""
from alembic import op
import sqlalchemy as sa

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "signals",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    op.execute("UPDATE signals SET updated_at = created_at WHERE updated_at IS NULL")


def downgrade() -> None:
    op.drop_column("signals", "updated_at")
