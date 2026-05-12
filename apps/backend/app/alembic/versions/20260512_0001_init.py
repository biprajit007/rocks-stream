"""initial schema"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '20260512_0001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    protocol = postgresql.ENUM('srt', 'rtmp', 'hls', name='protocol', create_type=False)
    stream_status = postgresql.ENUM('stopped', 'starting', 'running', 'error', 'degraded', name='streamstatus', create_type=False)
    output_type = postgresql.ENUM('srt', 'rtmp', 'hls', name='outputtype', create_type=False)
    logo_mode = postgresql.ENUM('corner', 'coordinates', name='logopositionmode', create_type=False)
    bind = op.get_bind()
    for enum_type in (protocol, stream_status, output_type, logo_mode):
        enum_type.create(bind, checkfirst=True)

    op.create_table('users',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('email', sa.String(length=255), nullable=False, unique=True),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('created_at', sa.DateTime(), nullable=False)
    )
    op.create_table('logo_assets',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('original_name', sa.String(length=255), nullable=False),
        sa.Column('stored_name', sa.String(length=255), nullable=False, unique=True),
        sa.Column('content_type', sa.String(length=128), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False)
    )
    op.create_table('streams',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('stream_key', sa.String(length=128), nullable=False, unique=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_enabled', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('abr_enabled', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('status', stream_status, nullable=False, server_default='stopped'),
        sa.Column('bitrate_kbps', sa.Integer(), nullable=True),
        sa.Column('resolution', sa.String(length=64), nullable=True),
        sa.Column('uptime_seconds', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('active_input_id', sa.Integer(), nullable=True),
        sa.Column('logo_asset_id', sa.Integer(), nullable=True),
        sa.Column('logo_enabled', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('logo_position_mode', logo_mode, nullable=False, server_default='corner'),
        sa.Column('logo_corner', sa.String(length=32), nullable=False, server_default='top-right'),
        sa.Column('logo_x', sa.Integer(), nullable=False, server_default='20'),
        sa.Column('logo_y', sa.Integer(), nullable=False, server_default='20'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['logo_asset_id'], ['logo_assets.id'], ondelete='SET NULL')
    )
    op.create_table('input_sources',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('stream_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('protocol', protocol, nullable=False),
        sa.Column('source_url', sa.Text(), nullable=False),
        sa.Column('priority', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('is_enabled', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('status', stream_status, nullable=False, server_default='stopped'),
        sa.Column('bitrate_kbps', sa.Integer(), nullable=True),
        sa.Column('resolution', sa.String(length=64), nullable=True),
        sa.Column('uptime_seconds', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['stream_id'], ['streams.id'], ondelete='CASCADE')
    )
    op.create_foreign_key('fk_stream_active_input', 'streams', 'input_sources', ['active_input_id'], ['id'], ondelete='SET NULL')
    op.create_table('output_targets',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('stream_id', sa.Integer(), nullable=False),
        sa.Column('output_type', output_type, nullable=False),
        sa.Column('is_enabled', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('port', sa.Integer(), nullable=True),
        sa.Column('path_suffix', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['stream_id'], ['streams.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('stream_id', 'output_type', name='uq_stream_output_type')
    )
    op.create_table('abr_profiles',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('stream_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=64), nullable=False),
        sa.Column('width', sa.Integer(), nullable=False),
        sa.Column('height', sa.Integer(), nullable=False),
        sa.Column('bitrate_kbps', sa.Integer(), nullable=False),
        sa.Column('is_enabled', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('playlist_name', sa.String(length=255), nullable=False),
        sa.ForeignKeyConstraint(['stream_id'], ['streams.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('stream_id', 'name', name='uq_stream_profile_name')
    )
    op.create_table('stream_runtime_state',
        sa.Column('stream_id', sa.Integer(), primary_key=True),
        sa.Column('engine_status', sa.String(length=64), nullable=False, server_default='stopped'),
        sa.Column('process_id', sa.Integer(), nullable=True),
        sa.Column('active_input_id', sa.Integer(), nullable=True),
        sa.Column('command', sa.Text(), nullable=True),
        sa.Column('preview_url', sa.Text(), nullable=True),
        sa.Column('details', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('last_heartbeat_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['stream_id'], ['streams.id'], ondelete='CASCADE')
    )
    op.create_table('stream_log_entries',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('stream_id', sa.Integer(), nullable=False),
        sa.Column('level', sa.String(length=32), nullable=False, server_default='info'),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['stream_id'], ['streams.id'], ondelete='CASCADE')
    )


def downgrade() -> None:
    op.drop_table('stream_log_entries')
    op.drop_table('stream_runtime_state')
    op.drop_table('abr_profiles')
    op.drop_table('output_targets')
    op.drop_constraint('fk_stream_active_input', 'streams', type_='foreignkey')
    op.drop_table('input_sources')
    op.drop_table('streams')
    op.drop_table('logo_assets')
    op.drop_table('users')
    bind = op.get_bind()
    sa.Enum(name='logopositionmode').drop(bind, checkfirst=True)
    sa.Enum(name='outputtype').drop(bind, checkfirst=True)
    sa.Enum(name='streamstatus').drop(bind, checkfirst=True)
    sa.Enum(name='protocol').drop(bind, checkfirst=True)
