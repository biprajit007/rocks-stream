"""add latency_ms to output_targets

Revision ID: 20260512_0002
Revises: 20260512_0001
Create Date: 2026-05-12 21:54:00
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20260512_0002'
down_revision = '20260512_0001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('output_targets', sa.Column('latency_ms', sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column('output_targets', 'latency_ms')
