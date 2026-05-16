"""add logo size fields

Revision ID: 20260514_0004
Revises: 20260513_0003
Create Date: 2026-05-14 15:40:00
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260514_0004"
down_revision = "20260513_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("streams", sa.Column("logo_width", sa.Integer(), nullable=False, server_default="120"))
    op.add_column("streams", sa.Column("logo_height", sa.Integer(), nullable=False, server_default="48"))


def downgrade() -> None:
    op.drop_column("streams", "logo_height")
    op.drop_column("streams", "logo_width")
