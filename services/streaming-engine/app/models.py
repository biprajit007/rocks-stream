import enum
from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Enum, ForeignKey, Integer, String, Text
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


class Stream(Base):
    __tablename__ = "streams"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    stream_key: Mapped[str] = mapped_column(String(128))
    abr_enabled: Mapped[bool] = mapped_column(Boolean)
    status: Mapped[StreamStatus] = mapped_column(Enum(StreamStatus))
    active_input_id: Mapped[int | None] = mapped_column(Integer)
    logo_asset_id: Mapped[int | None] = mapped_column(Integer)
    logo_enabled: Mapped[bool] = mapped_column(Boolean)
    logo_position_mode: Mapped[LogoPositionMode] = mapped_column(Enum(LogoPositionMode))
    logo_corner: Mapped[str] = mapped_column(String(32))
    logo_x: Mapped[int] = mapped_column(Integer)
    logo_y: Mapped[int] = mapped_column(Integer)
    logo_width: Mapped[int] = mapped_column(Integer)
    logo_height: Mapped[int] = mapped_column(Integer)

    input_sources: Mapped[list["InputSource"]] = relationship("InputSource", primaryjoin="Stream.id==InputSource.stream_id", order_by="InputSource.priority")
    output_targets: Mapped[list["OutputTarget"]] = relationship("OutputTarget", primaryjoin="Stream.id==OutputTarget.stream_id")
    abr_profiles: Mapped[list["AbrProfile"]] = relationship("AbrProfile", primaryjoin="Stream.id==AbrProfile.stream_id")
    runtime_state: Mapped["StreamRuntimeState | None"] = relationship("StreamRuntimeState", uselist=False)


class InputSource(Base):
    __tablename__ = "input_sources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    stream_id: Mapped[int] = mapped_column(ForeignKey("streams.id"))
    name: Mapped[str] = mapped_column(String(255))
    protocol: Mapped[Protocol] = mapped_column(Enum(Protocol))
    source_url: Mapped[str] = mapped_column(Text)
    priority: Mapped[int] = mapped_column(Integer)
    is_enabled: Mapped[bool] = mapped_column(Boolean)


class OutputTarget(Base):
    __tablename__ = "output_targets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    stream_id: Mapped[int] = mapped_column(ForeignKey("streams.id"))
    output_type: Mapped[OutputType] = mapped_column(Enum(OutputType))
    is_enabled: Mapped[bool] = mapped_column(Boolean)
    port: Mapped[int | None] = mapped_column(Integer)
    path_suffix: Mapped[str | None] = mapped_column(String(255))


class AbrProfile(Base):
    __tablename__ = "abr_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    stream_id: Mapped[int] = mapped_column(ForeignKey("streams.id"))
    name: Mapped[str] = mapped_column(String(64))
    width: Mapped[int] = mapped_column(Integer)
    height: Mapped[int] = mapped_column(Integer)
    bitrate_kbps: Mapped[int] = mapped_column(Integer)
    is_enabled: Mapped[bool] = mapped_column(Boolean)
    playlist_name: Mapped[str] = mapped_column(String(255))


class LogoAsset(Base):
    __tablename__ = "logo_assets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    original_name: Mapped[str] = mapped_column(String(255))
    stored_name: Mapped[str] = mapped_column(String(255))
    content_type: Mapped[str] = mapped_column(String(128))


class StreamRuntimeState(Base):
    __tablename__ = "stream_runtime_state"

    stream_id: Mapped[int] = mapped_column(ForeignKey("streams.id"), primary_key=True)
    engine_status: Mapped[str] = mapped_column(String(64))
    process_id: Mapped[int | None] = mapped_column(Integer)
    active_input_id: Mapped[int | None] = mapped_column(Integer)
    command: Mapped[str | None] = mapped_column(Text)
    preview_url: Mapped[str | None] = mapped_column(Text)
    details: Mapped[dict] = mapped_column(JSON)
    last_heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime)
    updated_at: Mapped[datetime] = mapped_column(DateTime)


class StreamLogEntry(Base):
    __tablename__ = "stream_log_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    stream_id: Mapped[int] = mapped_column(ForeignKey("streams.id"))
    level: Mapped[str] = mapped_column(String(32))
    message: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
