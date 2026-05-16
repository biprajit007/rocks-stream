"""add ad settings

Revision ID: 20260514_0005
Revises: 20260514_0004
Create Date: 2026-05-14 16:35:00
"""

from alembic import op
import sqlalchemy as sa


revision = '20260514_0005'
down_revision = '20260514_0004'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'ad_settings',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('provider', sa.String(length=128), nullable=False, server_default='Revive Adserver (open source)'),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('pre_roll', sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column('mid_roll', sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column('post_roll', sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column('video_ad', sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column('mid_roll_rules', sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
    )
    op.execute("""
        INSERT INTO ad_settings (id, provider, enabled, pre_roll, mid_roll, post_roll, video_ad, mid_roll_rules)
        VALUES (
          1,
          'Revive Adserver (open source)',
          false,
          '{"enabled": false, "tag_url": "", "offset": "start", "duration": "00:00:15", "skippable": false}',
          '{"enabled": false, "tag_url": "", "offset": "00:10:00", "duration": "00:00:30", "skippable": false}',
          '{"enabled": false, "tag_url": "", "offset": "end", "duration": "00:00:15", "skippable": false}',
          '{"enabled": false, "tag_url": "", "offset": "manual", "duration": "00:00:20", "skippable": false}',
          '["00:10:00"]'
        )
        ON CONFLICT (id) DO NOTHING
    """)


def downgrade() -> None:
    op.drop_table('ad_settings')
