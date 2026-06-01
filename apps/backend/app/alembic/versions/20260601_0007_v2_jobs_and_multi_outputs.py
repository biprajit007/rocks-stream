"""add v2 job tracking and allow repeated output targets"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260601_0007"
down_revision = "20260523_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    job_action = postgresql.ENUM(
        "start",
        "stop",
        "restart",
        "social_start",
        "social_stop",
        "social_restart",
        name="streamjobaction",
        create_type=False,
    )
    job_status = postgresql.ENUM("queued", "running", "completed", "failed", name="streamjobstatus", create_type=False)
    job_action.create(bind, checkfirst=True)
    job_status.create(bind, checkfirst=True)

    op.drop_constraint("uq_stream_output_type", "output_targets", type_="unique")

    op.create_table(
        "stream_jobs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("stream_id", sa.Integer(), nullable=False),
        sa.Column("action", job_action, nullable=False),
        sa.Column("status", job_status, nullable=False, server_default="queued"),
        sa.Column("engine", sa.String(length=64), nullable=False, server_default="ffmpeg"),
        sa.Column("worker_id", sa.String(length=128), nullable=True),
        sa.Column("process_id", sa.Integer(), nullable=True),
        sa.Column("request_payload", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("result_payload", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["stream_id"], ["streams.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_stream_jobs_stream_created", "stream_jobs", ["stream_id", "created_at"])

    op.create_table(
        "worker_heartbeats",
        sa.Column("worker_id", sa.String(length=128), primary_key=True),
        sa.Column("engine", sa.String(length=64), nullable=False, server_default="ffmpeg"),
        sa.Column("status", sa.String(length=64), nullable=False, server_default="idle"),
        sa.Column("active_stream_id", sa.Integer(), nullable=True),
        sa.Column("details", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("last_seen_at", sa.DateTime(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("worker_heartbeats")
    op.drop_index("ix_stream_jobs_stream_created", table_name="stream_jobs")
    op.drop_table("stream_jobs")
    op.create_unique_constraint("uq_stream_output_type", "output_targets", ["stream_id", "output_type"])

    bind = op.get_bind()
    sa.Enum(name="streamjobstatus").drop(bind, checkfirst=True)
    sa.Enum(name="streamjobaction").drop(bind, checkfirst=True)
