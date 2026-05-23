"""add stream playback auth flag"""

from alembic import op
import sqlalchemy as sa


revision = "20260523_0006"
down_revision = "20260514_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("streams", sa.Column("playback_auth_enabled", sa.Boolean(), nullable=False, server_default=sa.false()))


def downgrade() -> None:
    op.drop_column("streams", "playback_auth_enabled")
