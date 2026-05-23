import asyncio
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.deps import get_current_user, get_db
from app.models import InputSource, OutputType, SocialRestreamSettings, Stream, User
from app.schemas import SocialRestreamSettingsOut, SocialRestreamSettingsUpdate
from app.services.engine_client import post_engine
from app.services.url_builder import build_playback_urls

router = APIRouter(prefix="/social", tags=["social"])
SOCIAL_STOP_TASKS: dict[str, asyncio.Task] = {}


def _default_platform(name: str, ingest_url: str) -> dict:
    return {
        "enabled": False,
        "ingest_url": ingest_url,
        "stream_key": "",
        "notes": f"Set your {name} stream key here.",
        "video_path": "",
        "resolution": "1920x1080",
        "fps": 30,
        "video_bitrate": "4000k",
        "audio_bitrate": "128k",
        "rotate_every_hours": 6,
        "auto_rotation": False,
        "config_enabled": True,
        "stop_after_minutes": 0,
        "stop_at": "-",
        "extra_args": "",
        "live_id": "-",
        "post_id": "-",
        "pid": "-",
        "started": "-",
        "restarts": 0,
        "last_error": "-",
    }


def _default_settings() -> SocialRestreamSettings:
    return SocialRestreamSettings(
        id=1,
        source_stream_id=None,
        source_input_id=None,
        facebook=_default_platform("Facebook", "rtmps://live-api-s.facebook.com:443/rtmp/"),
        youtube=_default_platform("YouTube", "rtmp://a.rtmp.youtube.com/live2/"),
        tiktok=_default_platform("TikTok", "rtmps://live.tiktok.com:443/stream/"),
        twitch=_default_platform("Twitch", "rtmp://live.twitch.tv/app/"),
    )


def _ensure_schema(db: Session) -> None:
    db.execute(text("ALTER TABLE social_restream_settings ADD COLUMN IF NOT EXISTS source_input_id INTEGER"))
    db.commit()


def _cancel_stop_task(platform: str) -> None:
    task = SOCIAL_STOP_TASKS.pop(platform, None)
    if task and not task.done():
        task.cancel()


async def _auto_stop_social_platform(platform: str, stop_at_iso: str, delay_seconds: float) -> None:
    try:
        await asyncio.sleep(max(delay_seconds, 0))
        db = SessionLocal()
        try:
            _ensure_schema(db)
            settings = _get_or_create(db)
            attr = _platform_attr(platform)
            config = dict(getattr(settings, attr) or {})
            if not settings.source_stream_id or not config.get('enabled') or config.get('stop_at') != stop_at_iso:
                return
            try:
                await post_engine(f'/engine/social/{attr}/stop', {'source_stream_id': settings.source_stream_id})
                last_error = f"Auto-stopped after {int(config.get('stop_after_minutes') or 0)} minutes"
            except HTTPException as exc:
                last_error = str(exc.detail)
            _update_platform(settings, attr, {
                'enabled': False,
                'pid': '-',
                'stop_at': '-',
                'last_error': last_error,
            })
            settings.updated_at = datetime.utcnow()
            db.commit()
        finally:
            db.close()
    except asyncio.CancelledError:
        raise
    finally:
        SOCIAL_STOP_TASKS.pop(platform, None)


def _schedule_stop_task(platform: str, stop_at_iso: str) -> None:
    _cancel_stop_task(platform)
    if not stop_at_iso or stop_at_iso == '-':
        return
    try:
        stop_at = datetime.fromisoformat(stop_at_iso)
    except ValueError:
        return
    delay_seconds = (stop_at - datetime.utcnow()).total_seconds()
    SOCIAL_STOP_TASKS[platform] = asyncio.create_task(_auto_stop_social_platform(platform, stop_at_iso, delay_seconds))


def restore_scheduled_social_stops() -> None:
    db = SessionLocal()
    try:
        _ensure_schema(db)
        settings = _get_or_create(db)
        for platform in ('facebook', 'youtube', 'tiktok', 'twitch'):
            config = dict(getattr(settings, platform) or {})
            stop_at = config.get('stop_at') or '-'
            if config.get('enabled') and stop_at != '-':
                _schedule_stop_task(platform, stop_at)
            else:
                _cancel_stop_task(platform)
    finally:
        db.close()


def _get_or_create(db: Session) -> SocialRestreamSettings:
    settings = db.query(SocialRestreamSettings).filter(SocialRestreamSettings.id == 1).first()
    if settings:
        return settings
    settings = _default_settings()
    db.add(settings)
    db.commit()
    db.refresh(settings)
    return settings


def _serialize(settings: SocialRestreamSettings) -> SocialRestreamSettingsOut:
    payload = SocialRestreamSettingsOut.model_validate(settings, from_attributes=True)
    if settings.source_stream:
        payload.source_stream_name = settings.source_stream.name
        payload.source_stream_key = settings.source_stream.stream_key
    if settings.source_input:
        payload.source_input_name = settings.source_input.name
        payload.source_input_url = settings.source_input.source_url
    return payload


def _platform_attr(platform: str) -> str:
    mapping = {
        'facebook': 'facebook',
        'youtube': 'youtube',
        'tiktok': 'tiktok',
        'twitch': 'twitch',
    }
    if platform not in mapping:
        raise HTTPException(status_code=404, detail='Platform not found')
    return mapping[platform]


def _select_source_input(stream: Stream, preferred_input_id: int | None = None) -> InputSource | None:
    if preferred_input_id:
        for item in stream.input_sources:
            if item.id == preferred_input_id and item.is_enabled:
                return item
    if stream.active_input_id:
        for item in stream.input_sources:
            if item.id == stream.active_input_id and item.is_enabled:
                return item
    enabled_inputs = [item for item in stream.input_sources if item.is_enabled]
    if not enabled_inputs:
        return None
    return sorted(enabled_inputs, key=lambda item: item.priority)[0]


def _source_details(stream: Stream, preferred_input_id: int | None = None) -> tuple[str | None, str | None]:
    if preferred_input_id:
        source_input = _select_source_input(stream, preferred_input_id)
        if source_input:
            return source_input.source_url, source_input.protocol.value

    rtmp_output = next((item for item in stream.output_targets if item.is_enabled and item.output_type == OutputType.rtmp), None)
    if rtmp_output:
        path_suffix = rtmp_output.path_suffix or stream.stream_key
        return f"rtmp://nginx:1935/live/{path_suffix}", OutputType.rtmp.value

    source_input = _select_source_input(stream)
    if source_input:
        return source_input.source_url, source_input.protocol.value

    hls_output = next((item for item in stream.output_targets if item.is_enabled and item.output_type == OutputType.hls), None)
    if hls_output:
        playlist_key = "main" if getattr(stream, "is_primary", False) else stream.stream_key
        return f"http://nginx/live/{playlist_key}/index.m3u8", OutputType.hls.value

    urls = build_playback_urls(stream)
    return urls.rtmp or urls.main_hls or urls.master_hls or urls.hls or urls.srt, None


def _valid_stream_key(value: str | None) -> bool:
    if not value:
        return False
    value = value.strip()
    return bool(value) and not value.startswith("paste-")


def _update_platform(settings_obj: SocialRestreamSettings, attr: str, patch: dict) -> None:
    current = dict(getattr(settings_obj, attr) or {})
    current.update(patch)
    setattr(settings_obj, attr, current)


def _set_platform_error(settings_obj: SocialRestreamSettings, attr: str, message: str) -> None:
    _update_platform(settings_obj, attr, {
        'enabled': False,
        'last_error': message,
        'pid': '-',
    })


@router.get("", response_model=SocialRestreamSettingsOut)
def get_social_settings(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    _ensure_schema(db)
    return _serialize(_get_or_create(db))


@router.put("", response_model=SocialRestreamSettingsOut)
def update_social_settings(payload: SocialRestreamSettingsUpdate, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    _ensure_schema(db)
    settings = _get_or_create(db)
    stream = None
    if payload.source_stream_id is not None:
        stream = db.query(Stream).filter(Stream.id == payload.source_stream_id).first()
        if not stream:
            raise HTTPException(status_code=404, detail="Source stream not found")
        settings.source_stream_id = stream.id
    else:
        settings.source_stream_id = None
        settings.source_input_id = None

    if payload.source_input_id is not None:
        if not stream:
            stream = db.query(Stream).filter(Stream.id == settings.source_stream_id).first() if settings.source_stream_id else None
        if not stream:
            raise HTTPException(status_code=400, detail="Select a source stream first")
        selected_input = next((item for item in stream.input_sources if item.id == payload.source_input_id), None)
        if not selected_input:
            raise HTTPException(status_code=404, detail="Source input not found for selected stream")
        settings.source_input_id = selected_input.id
    else:
        settings.source_input_id = None

    settings.facebook = payload.facebook.model_dump()
    settings.youtube = payload.youtube.model_dump()
    settings.tiktok = payload.tiktok.model_dump()
    settings.twitch = payload.twitch.model_dump()
    settings.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(settings)
    for platform in ('facebook', 'youtube', 'tiktok', 'twitch'):
        config = dict(getattr(settings, platform) or {})
        if not config.get('enabled') or not config.get('stop_at') or config.get('stop_at') == '-':
            _cancel_stop_task(platform)
    return _serialize(settings)


@router.post('/{platform}/start', response_model=SocialRestreamSettingsOut)
async def start_social_platform(platform: str, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    _ensure_schema(db)
    settings = _get_or_create(db)
    attr = _platform_attr(platform)
    config = dict(getattr(settings, attr) or {})
    if not settings.source_stream_id:
        raise HTTPException(status_code=400, detail='Select a source stream first')
    stream = db.query(Stream).filter(Stream.id == settings.source_stream_id).first()
    if not stream:
        raise HTTPException(status_code=404, detail='Source stream not found')
    source_url, source_protocol = _source_details(stream, settings.source_input_id)
    if not source_url:
        raise HTTPException(status_code=400, detail='Source stream needs a working enabled input or output before social restream can start')
    if not config.get('ingest_url') or not _valid_stream_key(config.get('stream_key')):
        raise HTTPException(status_code=400, detail='Platform ingest URL and stream key are required')

    try:
        if not stream.runtime_state or stream.runtime_state.engine_status != 'running':
            await post_engine(f'/engine/streams/{stream.id}/start', {'stream_id': stream.id, 'action': 'start'})
            db.expire_all()
            stream = db.query(Stream).filter(Stream.id == settings.source_stream_id).first()
            source_url, source_protocol = _source_details(stream, settings.source_input_id) if stream else (None, None)
            if not source_url:
                raise HTTPException(status_code=400, detail='Source stream could not expose a playable source after startup')

        result = await post_engine(f'/engine/social/{attr}/start', {
            'source_stream_id': stream.id,
            'source_url': source_url,
            'source_protocol': source_protocol,
            'ingest_url': config.get('ingest_url'),
            'stream_key': config.get('stream_key'),
            'resolution': config.get('resolution', '1920x1080'),
            'fps': config.get('fps', 30),
            'video_bitrate': config.get('video_bitrate', '4000k'),
            'audio_bitrate': config.get('audio_bitrate', '128k'),
            'extra_args': config.get('extra_args', ''),
        })
    except HTTPException as exc:
        _set_platform_error(settings, attr, str(exc.detail))
        settings.updated_at = datetime.utcnow()
        db.commit()
        raise

    _update_platform(settings, attr, {
        'enabled': True,
        'config_enabled': True,
        'pid': str(result.get('process_id') or '-'),
        'started': datetime.utcnow().isoformat(),
        'last_error': '-',
        'stop_at': '-',
        'live_id': config.get('live_id') or f"live-{stream.id}",
        'post_id': config.get('post_id') or '-',
        'restarts': int(config.get('restarts') or 0),
    })
    stop_after_minutes = int(config.get('stop_after_minutes') or 0)
    if stop_after_minutes > 0:
        stop_at = (datetime.utcnow() + timedelta(minutes=stop_after_minutes)).isoformat()
        _update_platform(settings, attr, {'stop_at': stop_at})
        _schedule_stop_task(attr, stop_at)
    else:
        _cancel_stop_task(attr)
    settings.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(settings)
    return _serialize(settings)


@router.post('/{platform}/stop', response_model=SocialRestreamSettingsOut)
async def stop_social_platform(platform: str, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    _ensure_schema(db)
    settings = _get_or_create(db)
    attr = _platform_attr(platform)
    config = dict(getattr(settings, attr) or {})
    if settings.source_stream_id:
        try:
            await post_engine(f'/engine/social/{attr}/stop', {'source_stream_id': settings.source_stream_id})
        except HTTPException as exc:
            _set_platform_error(settings, attr, str(exc.detail))
            settings.updated_at = datetime.utcnow()
            db.commit()
            raise
    _update_platform(settings, attr, {
        'enabled': False,
        'config_enabled': bool(config.get('config_enabled', True)),
        'pid': '-',
        'stop_at': '-',
        'last_error': config.get('last_error') or '-',
    })
    _cancel_stop_task(attr)
    settings.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(settings)
    return _serialize(settings)


@router.post('/{platform}/restart', response_model=SocialRestreamSettingsOut)
async def restart_social_platform(platform: str, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    _ensure_schema(db)
    settings = _get_or_create(db)
    attr = _platform_attr(platform)
    config = dict(getattr(settings, attr) or {})
    if not settings.source_stream_id:
        raise HTTPException(status_code=400, detail='Select a source stream first')
    stream = db.query(Stream).filter(Stream.id == settings.source_stream_id).first()
    if not stream:
        raise HTTPException(status_code=404, detail='Source stream not found')
    source_url, source_protocol = _source_details(stream, settings.source_input_id)
    if not source_url:
        raise HTTPException(status_code=400, detail='Source stream needs a working enabled input or output before social restream can restart')
    if not config.get('ingest_url') or not _valid_stream_key(config.get('stream_key')):
        raise HTTPException(status_code=400, detail='Platform ingest URL and stream key are required')

    try:
        if not stream.runtime_state or stream.runtime_state.engine_status != 'running':
            await post_engine(f'/engine/streams/{stream.id}/start', {'stream_id': stream.id, 'action': 'start'})
            db.expire_all()
            stream = db.query(Stream).filter(Stream.id == settings.source_stream_id).first()
            source_url, source_protocol = _source_details(stream, settings.source_input_id) if stream else (None, None)
            if not source_url:
                raise HTTPException(status_code=400, detail='Source stream could not expose a playable source after startup')

        result = await post_engine(f'/engine/social/{attr}/restart', {
            'source_stream_id': stream.id,
            'source_url': source_url,
            'source_protocol': source_protocol,
            'ingest_url': config.get('ingest_url'),
            'stream_key': config.get('stream_key'),
            'resolution': config.get('resolution', '1920x1080'),
            'fps': config.get('fps', 30),
            'video_bitrate': config.get('video_bitrate', '4000k'),
            'audio_bitrate': config.get('audio_bitrate', '128k'),
            'extra_args': config.get('extra_args', ''),
        })
    except HTTPException as exc:
        _set_platform_error(settings, attr, str(exc.detail))
        settings.updated_at = datetime.utcnow()
        db.commit()
        raise

    _update_platform(settings, attr, {
        'enabled': True,
        'config_enabled': True,
        'restarts': int(config.get('restarts') or 0) + 1,
        'pid': str(result.get('process_id') or '-'),
        'started': datetime.utcnow().isoformat(),
        'last_error': '-',
        'stop_at': '-',
    })
    stop_after_minutes = int(config.get('stop_after_minutes') or 0)
    if stop_after_minutes > 0:
        stop_at = (datetime.utcnow() + timedelta(minutes=stop_after_minutes)).isoformat()
        _update_platform(settings, attr, {'stop_at': stop_at})
        _schedule_stop_task(attr, stop_at)
    else:
        _cancel_stop_task(attr)
    settings.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(settings)
    return _serialize(settings)
