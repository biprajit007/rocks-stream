from datetime import datetime
from typing import Any

from pydantic import AliasChoices, BaseModel, EmailStr, Field

from app.models import LogoPositionMode, OutputType, Protocol, StreamStatus


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LoginRequest(BaseModel):
    username: str = Field(validation_alias=AliasChoices("username", "email"))
    password: str


class UserOut(BaseModel):
    id: int
    email: EmailStr
    is_active: bool

    model_config = {"from_attributes": True}


class InputSourceBase(BaseModel):
    name: str
    protocol: Protocol
    source_url: str
    priority: int = 1
    is_enabled: bool = True


class InputSourceCreate(InputSourceBase):
    pass


class InputSourceUpdate(BaseModel):
    name: str | None = None
    protocol: Protocol | None = None
    source_url: str | None = None
    priority: int | None = None
    is_enabled: bool | None = None


class InputSourceOut(InputSourceBase):
    id: int
    status: StreamStatus
    bitrate_kbps: int | None = None
    resolution: str | None = None
    uptime_seconds: int = 0

    model_config = {"from_attributes": True}


class OutputTargetBase(BaseModel):
    output_type: OutputType
    is_enabled: bool = True
    port: int | None = None
    latency_ms: int | None = None
    path_suffix: str | None = None


class OutputTargetCreate(OutputTargetBase):
    pass


class OutputTargetUpdate(BaseModel):
    is_enabled: bool | None = None
    port: int | None = None
    latency_ms: int | None = None
    path_suffix: str | None = None


class OutputTargetOut(OutputTargetBase):
    id: int

    model_config = {"from_attributes": True}


class AbrProfileBase(BaseModel):
    name: str
    width: int
    height: int
    bitrate_kbps: int
    is_enabled: bool = True
    playlist_name: str


class AbrProfileCreate(AbrProfileBase):
    pass


class AbrProfileUpdate(BaseModel):
    bitrate_kbps: int | None = None
    is_enabled: bool | None = None
    width: int | None = None
    height: int | None = None
    playlist_name: str | None = None


class AbrProfileOut(AbrProfileBase):
    id: int

    model_config = {"from_attributes": True}


class StreamBase(BaseModel):
    name: str
    stream_key: str = Field(pattern=r"^[a-zA-Z0-9_-]+$")
    description: str | None = None
    is_enabled: bool = True
    abr_enabled: bool = False
    playback_auth_enabled: bool = False
    is_primary: bool = False
    logo_enabled: bool = False
    logo_position_mode: LogoPositionMode = LogoPositionMode.corner
    logo_corner: str = "top-right"
    logo_x: int = 20
    logo_y: int = 20
    logo_width: int = 120
    logo_height: int = 48


class StreamCreate(StreamBase):
    inputs: list[InputSourceCreate] = Field(default_factory=list)
    outputs: list[OutputTargetCreate] = Field(default_factory=list)
    abr_profiles: list[AbrProfileCreate] = Field(default_factory=list)


class StreamUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    is_enabled: bool | None = None
    abr_enabled: bool | None = None
    playback_auth_enabled: bool | None = None
    is_primary: bool | None = None
    logo_enabled: bool | None = None
    logo_position_mode: LogoPositionMode | None = None
    logo_corner: str | None = None
    logo_x: int | None = None
    logo_y: int | None = None
    logo_width: int | None = None
    logo_height: int | None = None


class PlaybackUrls(BaseModel):
    hls: str | None = None
    master_hls: str | None = None
    main_hls: str | None = None
    rtmp: str | None = None
    srt: str | None = None


class RuntimeStateOut(BaseModel):
    engine_status: str
    process_id: int | None = None
    active_input_id: int | None = None
    command: str | None = None
    preview_url: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)
    last_heartbeat_at: datetime | None = None
    updated_at: datetime

    model_config = {"from_attributes": True}


class LogEntryOut(BaseModel):
    id: int
    level: str
    message: str
    created_at: datetime

    model_config = {"from_attributes": True}


class StreamOut(StreamBase):
    id: int
    status: StreamStatus
    bitrate_kbps: int | None = None
    resolution: str | None = None
    uptime_seconds: int = 0
    active_input_id: int | None = None
    logo_asset_id: int | None = None
    created_at: datetime
    updated_at: datetime
    input_sources: list[InputSourceOut] = Field(default_factory=list)
    output_targets: list[OutputTargetOut] = Field(default_factory=list)
    abr_profiles: list[AbrProfileOut] = Field(default_factory=list)
    runtime_state: RuntimeStateOut | None = None
    playback_urls: PlaybackUrls = Field(default_factory=PlaybackUrls)

    model_config = {"from_attributes": True}


class EngineCommandResponse(BaseModel):
    ok: bool
    message: str
    runtime: RuntimeStateOut | None = None


class AdSlotConfig(BaseModel):
    enabled: bool = False
    tag_url: str = ""
    offset: str = ""
    duration: str = ""
    skippable: bool = False


class AdSettingsBase(BaseModel):
    provider: str = "Revive Adserver (open source)"
    enabled: bool = False
    pre_roll: AdSlotConfig = Field(default_factory=AdSlotConfig)
    mid_roll: AdSlotConfig = Field(default_factory=AdSlotConfig)
    post_roll: AdSlotConfig = Field(default_factory=AdSlotConfig)
    video_ad: AdSlotConfig = Field(default_factory=AdSlotConfig)
    mid_roll_rules: list[str] = Field(default_factory=list)


class AdSettingsUpdate(AdSettingsBase):
    pass


class AdSettingsOut(AdSettingsBase):
    id: int
    updated_at: datetime

    model_config = {"from_attributes": True}


class PlayerAdConfigOut(BaseModel):
    enabled: bool = False
    provider: str = "Revive Adserver (open source)"
    stream_key: str | None = None
    pre_roll: AdSlotConfig | None = None
    mid_roll: AdSlotConfig | None = None
    post_roll: AdSlotConfig | None = None
    video_ad: AdSlotConfig | None = None
    mid_roll_rules: list[str] = Field(default_factory=list)
    player_hints: dict[str, str] = Field(default_factory=dict)


class SocialPlatformConfig(BaseModel):
    enabled: bool = False
    ingest_url: str = ""
    stream_key: str = ""
    notes: str = ""
    video_path: str = ""
    resolution: str = "1920x1080"
    fps: int = 30
    video_bitrate: str = "4000k"
    audio_bitrate: str = "128k"
    rotate_every_hours: int = 6
    auto_rotation: bool = False
    config_enabled: bool = True
    stop_after_minutes: int = 0
    stop_at: str = "-"
    extra_args: str = ""
    live_id: str = "-"
    post_id: str = "-"
    pid: str = "-"
    started: str = "-"
    restarts: int = 0
    last_error: str = "-"


class SocialRestreamSettingsBase(BaseModel):
    source_stream_id: int | None = None
    source_input_id: int | None = None
    facebook: SocialPlatformConfig = Field(default_factory=SocialPlatformConfig)
    youtube: SocialPlatformConfig = Field(default_factory=SocialPlatformConfig)
    tiktok: SocialPlatformConfig = Field(default_factory=SocialPlatformConfig)
    twitch: SocialPlatformConfig = Field(default_factory=SocialPlatformConfig)


class SocialRestreamSettingsUpdate(SocialRestreamSettingsBase):
    pass


class SocialRestreamSettingsOut(SocialRestreamSettingsBase):
    id: int
    updated_at: datetime
    source_stream_name: str | None = None
    source_stream_key: str | None = None
    source_input_name: str | None = None
    source_input_url: str | None = None

    model_config = {"from_attributes": True}
