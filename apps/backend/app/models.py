import enum
from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Enum, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class Protocol(str, enum.Enum):
    srt = "srt"
    rtmp = "rtmp"
    hls = "hls"


class StreamStatus(str, enum.Enum):
    stopped = "stopped"
    starting = "starting"
    running = "running"
    error = "error"
    degraded = "degraded"


class OutputType(str, enum.Enum):
    srt = "srt"
    rtmp = "rtmp"
    hls = "hls"


class LogoPositionMode(str, enum.Enum):
    corner = "corner"
    coordinates = "coordinates"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Stream(Base):
    __tablename__ = "streams"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    stream_key: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    abr_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    playback_auth_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[StreamStatus] = mapped_column(Enum(StreamStatus), default=StreamStatus.stopped)
    bitrate_kbps: Mapped[int | None] = mapped_column(Integer)
    resolution: Mapped[str | None] = mapped_column(String(64))
    uptime_seconds: Mapped[int] = mapped_column(Integer, default=0)
    active_input_id: Mapped[int | None] = mapped_column(ForeignKey("input_sources.id", ondelete="SET NULL"))
    logo_asset_id: Mapped[int | None] = mapped_column(ForeignKey("logo_assets.id", ondelete="SET NULL"))
    logo_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    logo_position_mode: Mapped[LogoPositionMode] = mapped_column(Enum(LogoPositionMode), default=LogoPositionMode.corner)
    logo_corner: Mapped[str] = mapped_column(String(32), default="top-right")
    logo_x: Mapped[int] = mapped_column(Integer, default=20)
    logo_y: Mapped[int] = mapped_column(Integer, default=20)
    logo_width: Mapped[int] = mapped_column(Integer, default=120)
    logo_height: Mapped[int] = mapped_column(Integer, default=48)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    input_sources: Mapped[list["InputSource"]] = relationship("InputSource", back_populates="stream", foreign_keys="InputSource.stream_id", cascade="all, delete-orphan", order_by="InputSource.priority")
    output_targets: Mapped[list["OutputTarget"]] = relationship("OutputTarget", back_populates="stream", cascade="all, delete-orphan")
    abr_profiles: Mapped[list["AbrProfile"]] = relationship("AbrProfile", back_populates="stream", cascade="all, delete-orphan")
    runtime_state: Mapped["StreamRuntimeState | None"] = relationship("StreamRuntimeState", back_populates="stream", uselist=False, cascade="all, delete-orphan")
    logs: Mapped[list["StreamLogEntry"]] = relationship("StreamLogEntry", back_populates="stream", cascade="all, delete-orphan")
    logo_asset: Mapped["LogoAsset | None"] = relationship("LogoAsset", foreign_keys=[logo_asset_id])


class InputSource(Base):
    __tablename__ = "input_sources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    stream_id: Mapped[int] = mapped_column(ForeignKey("streams.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    protocol: Mapped[Protocol] = mapped_column(Enum(Protocol), nullable=False)
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=1)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    status: Mapped[StreamStatus] = mapped_column(Enum(StreamStatus), default=StreamStatus.stopped)
    bitrate_kbps: Mapped[int | None] = mapped_column(Integer)
    resolution: Mapped[str | None] = mapped_column(String(64))
    uptime_seconds: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    stream: Mapped[Stream] = relationship("Stream", back_populates="input_sources", foreign_keys=[stream_id])


class OutputTarget(Base):
    __tablename__ = "output_targets"
    __table_args__ = (UniqueConstraint("stream_id", "output_type", name="uq_stream_output_type"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    stream_id: Mapped[int] = mapped_column(ForeignKey("streams.id", ondelete="CASCADE"), nullable=False)
    output_type: Mapped[OutputType] = mapped_column(Enum(OutputType), nullable=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    port: Mapped[int | None] = mapped_column(Integer)
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    path_suffix: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    stream: Mapped[Stream] = relationship("Stream", back_populates="output_targets")


class AbrProfile(Base):
    __tablename__ = "abr_profiles"
    __table_args__ = (UniqueConstraint("stream_id", "name", name="uq_stream_profile_name"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    stream_id: Mapped[int] = mapped_column(ForeignKey("streams.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    width: Mapped[int] = mapped_column(Integer, nullable=False)
    height: Mapped[int] = mapped_column(Integer, nullable=False)
    bitrate_kbps: Mapped[int] = mapped_column(Integer, nullable=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    playlist_name: Mapped[str] = mapped_column(String(255), nullable=False)

    stream: Mapped[Stream] = relationship("Stream", back_populates="abr_profiles")


class LogoAsset(Base):
    __tablename__ = "logo_assets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    original_name: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    content_type: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class StreamRuntimeState(Base):
    __tablename__ = "stream_runtime_state"

    stream_id: Mapped[int] = mapped_column(ForeignKey("streams.id", ondelete="CASCADE"), primary_key=True)
    engine_status: Mapped[str] = mapped_column(String(64), default="stopped")
    process_id: Mapped[int | None] = mapped_column(Integer)
    active_input_id: Mapped[int | None] = mapped_column(Integer)
    command: Mapped[str | None] = mapped_column(Text)
    preview_url: Mapped[str | None] = mapped_column(Text)
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    last_heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    stream: Mapped[Stream] = relationship("Stream", back_populates="runtime_state")


class StreamLogEntry(Base):
    __tablename__ = "stream_log_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    stream_id: Mapped[int] = mapped_column(ForeignKey("streams.id", ondelete="CASCADE"), nullable=False)
    level: Mapped[str] = mapped_column(String(32), default="info")
    message: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    stream: Mapped[Stream] = relationship("Stream", back_populates="logs")


class AdSettings(Base):
    __tablename__ = "ad_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    provider: Mapped[str] = mapped_column(String(128), default="Revive Adserver (open source)")
    enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    pre_roll: Mapped[dict] = mapped_column(JSON, default=dict)
    mid_roll: Mapped[dict] = mapped_column(JSON, default=dict)
    post_roll: Mapped[dict] = mapped_column(JSON, default=dict)
    video_ad: Mapped[dict] = mapped_column(JSON, default=dict)
    mid_roll_rules: Mapped[list] = mapped_column(JSON, default=list)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class SocialRestreamSettings(Base):
    __tablename__ = "social_restream_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    source_stream_id: Mapped[int | None] = mapped_column(ForeignKey("streams.id", ondelete="SET NULL"), nullable=True)
    source_input_id: Mapped[int | None] = mapped_column(ForeignKey("input_sources.id", ondelete="SET NULL"), nullable=True)
    facebook: Mapped[dict] = mapped_column(JSON, default=dict)
    youtube: Mapped[dict] = mapped_column(JSON, default=dict)
    tiktok: Mapped[dict] = mapped_column(JSON, default=dict)
    twitch: Mapped[dict] = mapped_column(JSON, default=dict)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    source_stream: Mapped[Stream | None] = relationship("Stream", foreign_keys=[source_stream_id])
    source_input: Mapped[InputSource | None] = relationship("InputSource", foreign_keys=[source_input_id])
