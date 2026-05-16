"""add is_primary to streams

Revision ID: 20260513_0003
Revises: 20260512_0002
Create Date: 2026-05-13 15:24:00
"""

from alembic import op
import sqlalchemy as sa


revision = '20260513_0003'
down_revision = '20260512_0002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('streams', sa.Column('is_primary', sa.Boolean(), nullable=False, server_default=sa.false()))
    op.alter_column('streams', 'is_primary', server_default=None)


def downgrade() -> None:
    op.drop_column('streams', 'is_primary')
