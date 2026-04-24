"""create stock_pool table

Revision ID: 003
Revises: 002
Create Date: 2026-04-25

"""
from alembic import op
import sqlalchemy as sa

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "stock_pool",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("stock_code", sa.String(10), nullable=False, index=True),
        sa.Column("stock_name", sa.String(50), nullable=False),
        sa.Column("yield_pct", sa.Float(), nullable=False, server_default="0"),
        sa.Column("market_cap", sa.Float(), nullable=False, server_default="0"),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("stock_pool")
