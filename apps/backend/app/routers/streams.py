import os
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session, joinedload

from app.core.config import settings
from app.deps import get_current_user, get_db
from app.models import AbrProfile, InputSource, LogoAsset, OutputTarget, Stream, StreamLogEntry, StreamRuntimeState, StreamStatus, User
from app.schemas import (
    AbrProfileCreate,
    AbrProfileOut,
    AbrProfileUpdate,
    EngineCommandResponse,
    InputSourceCreate,
    InputSourceOut,
    InputSourceUpdate,
    LogEntryOut,
    OutputTargetCreate,
    OutputTargetOut,
    OutputTargetUpdate,
    PlaybackUrls,
    RuntimeStateOut,
    StreamCreate,
    StreamOut,
    StreamUpdate,
)
from app.services.engine_client import post_engine
from app.services.main_stream import sync_main_stream_alias
from app.services.seed import DEFAULT_ABR_PROFILES
from app.services.url_builder import build_playback_urls

router = APIRouter(prefix="/streams", tags=["streams"])


def _base_query(db: Session):
    return db.query(Stream).options(
        joinedload(Stream.input_sources),
        joinedload(Stream.output_targets),
        joinedload(Stream.abr_profiles),
        joinedload(Stream.runtime_state),
    )


def _get_stream_or_404(db: Session, stream_id: int) -> Stream:
    stream = _base_query(db).filter(Stream.id == stream_id).first()
    if not stream:
        raise HTTPException(status_code=404, detail="Stream not found")
    return stream


def _serialize_stream(stream: Stream) -> StreamOut:
    data = StreamOut.model_validate(stream, from_attributes=True)
    data.playback_urls = build_playback_urls(stream)
    return data


@router.get("", response_model=list[StreamOut])
def list_streams(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return [_serialize_stream(stream) for stream in _base_query(db).order_by(Stream.created_at.desc()).all()]


@router.post("", response_model=StreamOut)
def create_stream(payload: StreamCreate, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    if payload.is_primary:
        db.query(Stream).update({Stream.is_primary: False})

    existing = db.query(Stream).filter(Stream.stream_key == payload.stream_key).first()
    if existing:
        raise HTTPException(status_code=409, detail="Stream key already exists")

    stream = Stream(
        name=payload.name,
        stream_key=payload.stream_key,
        description=payload.description,
        is_enabled=payload.is_enabled,
        abr_enabled=payload.abr_enabled,
        is_primary=payload.is_primary,
        logo_enabled=payload.logo_enabled,
        logo_position_mode=payload.logo_position_mode,
        logo_corner=payload.logo_corner,
        logo_x=payload.logo_x,
        logo_y=payload.logo_y,
        logo_width=payload.logo_width,
        logo_height=payload.logo_height,
    )
    db.add(stream)
    db.flush()

    for item in payload.inputs:
        db.add(InputSource(stream_id=stream.id, **item.model_dump()))
    for item in payload.outputs:
        db.add(OutputTarget(stream_id=stream.id, **item.model_dump()))

    profiles = payload.abr_profiles or ([AbrProfileCreate(**profile) for profile in DEFAULT_ABR_PROFILES] if payload.abr_enabled else [])
    for item in profiles:
        db.add(AbrProfile(stream_id=stream.id, **item.model_dump()))

    db.add(StreamRuntimeState(stream_id=stream.id, engine_status="stopped", details={}))
    db.add(StreamLogEntry(stream_id=stream.id, level="info", message="Stream created"))
    db.commit()
    sync_main_stream_alias(db)
    return _serialize_stream(_get_stream_or_404(db, stream.id))


@router.get("/{stream_id}", response_model=StreamOut)
def get_stream(stream_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return _serialize_stream(_get_stream_or_404(db, stream_id))


@router.patch("/{stream_id}", response_model=StreamOut)
def update_stream(stream_id: int, payload: StreamUpdate, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    stream = _get_stream_or_404(db, stream_id)
    updates = payload.model_dump(exclude_unset=True)
    if updates.get("is_primary"):
        db.query(Stream).update({Stream.is_primary: False})
    for key, value in updates.items():
        setattr(stream, key, value)
    stream.updated_at = datetime.utcnow()
    db.add(StreamLogEntry(stream_id=stream.id, level="info", message="Stream updated"))
    db.commit()
    sync_main_stream_alias(db)
    return _serialize_stream(_get_stream_or_404(db, stream_id))


@router.delete("/{stream_id}")
def delete_stream(stream_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    stream = _get_stream_or_404(db, stream_id)
    db.delete(stream)
    db.commit()
    sync_main_stream_alias(db)
    return {"ok": True}


@router.post("/{stream_id}/go-live", response_model=StreamOut)
def go_live(stream_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    stream = _get_stream_or_404(db, stream_id)
    db.query(Stream).update({Stream.is_primary: False})
    stream.is_primary = True
    stream.updated_at = datetime.utcnow()
    db.add(StreamLogEntry(stream_id=stream.id, level="info", message="Stream set as main live stream"))
    db.commit()
    sync_main_stream_alias(db)
    return _serialize_stream(_get_stream_or_404(db, stream_id))


@router.post("/{stream_id}/inputs", response_model=InputSourceOut)
def create_input(stream_id: int, payload: InputSourceCreate, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    _get_stream_or_404(db, stream_id)
    item = InputSource(stream_id=stream_id, **payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.patch("/{stream_id}/inputs/{input_id}", response_model=InputSourceOut)
def update_input(stream_id: int, input_id: int, payload: InputSourceUpdate, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    item = db.query(InputSource).filter(InputSource.stream_id == stream_id, InputSource.id == input_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Input not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, key, value)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/{stream_id}/inputs/{input_id}")
def delete_input(stream_id: int, input_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    item = db.query(InputSource).filter(InputSource.stream_id == stream_id, InputSource.id == input_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Input not found")
    db.delete(item)
    db.commit()
    return {"ok": True}


@router.post("/{stream_id}/outputs", response_model=OutputTargetOut)
def create_output(stream_id: int, payload: OutputTargetCreate, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    _get_stream_or_404(db, stream_id)
    item = OutputTarget(stream_id=stream_id, **payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.patch("/{stream_id}/outputs/{output_id}", response_model=OutputTargetOut)
def update_output(stream_id: int, output_id: int, payload: OutputTargetUpdate, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    item = db.query(OutputTarget).filter(OutputTarget.stream_id == stream_id, OutputTarget.id == output_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Output not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, key, value)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/{stream_id}/outputs/{output_id}")
def delete_output(stream_id: int, output_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    item = db.query(OutputTarget).filter(OutputTarget.stream_id == stream_id, OutputTarget.id == output_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Output not found")
    db.delete(item)
    db.commit()
    return {"ok": True}


@router.post("/{stream_id}/abr-profiles", response_model=AbrProfileOut)
def create_profile(stream_id: int, payload: AbrProfileCreate, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    _get_stream_or_404(db, stream_id)
    item = AbrProfile(stream_id=stream_id, **payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.patch("/{stream_id}/abr-profiles/{profile_id}", response_model=AbrProfileOut)
def update_profile(stream_id: int, profile_id: int, payload: AbrProfileUpdate, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    item = db.query(AbrProfile).filter(AbrProfile.stream_id == stream_id, AbrProfile.id == profile_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Profile not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, key, value)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/{stream_id}/abr-profiles/{profile_id}")
def delete_profile(stream_id: int, profile_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    item = db.query(AbrProfile).filter(AbrProfile.stream_id == stream_id, AbrProfile.id == profile_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Profile not found")
    db.delete(item)
    db.commit()
    return {"ok": True}


@router.post("/{stream_id}/logo", response_model=StreamOut)
def upload_logo(stream_id: int, file: UploadFile = File(...), db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    stream = _get_stream_or_404(db, stream_id)
    os.makedirs(settings.logos_root, exist_ok=True)
    suffix = os.path.splitext(file.filename or "logo.png")[1] or ".png"
    stored_name = f"{uuid.uuid4().hex}{suffix}"
    target_path = os.path.join(settings.logos_root, stored_name)
    with open(target_path, "wb") as handle:
        handle.write(file.file.read())
    asset = LogoAsset(original_name=file.filename or stored_name, stored_name=stored_name, content_type=file.content_type or "application/octet-stream")
    db.add(asset)
    db.flush()
    stream.logo_asset_id = asset.id
    db.add(StreamLogEntry(stream_id=stream.id, level="info", message="Logo uploaded"))
    db.commit()
    return _serialize_stream(_get_stream_or_404(db, stream_id))


@router.get("/{stream_id}/playback-urls", response_model=PlaybackUrls)
def get_playback_urls(stream_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    stream = _get_stream_or_404(db, stream_id)
    return build_playback_urls(stream)


@router.get("/{stream_id}/runtime", response_model=RuntimeStateOut)
def get_runtime(stream_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    stream = _get_stream_or_404(db, stream_id)
    if not stream.runtime_state:
        raise HTTPException(status_code=404, detail="Runtime state not found")
    return stream.runtime_state


@router.get("/{stream_id}/logs", response_model=list[LogEntryOut])
def get_logs(stream_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    _get_stream_or_404(db, stream_id)
    return db.query(StreamLogEntry).filter(StreamLogEntry.stream_id == stream_id).order_by(StreamLogEntry.created_at.desc()).limit(200).all()


async def _engine_action(stream_id: int, action: str, db: Session) -> EngineCommandResponse:
    stream = _get_stream_or_404(db, stream_id)
    payload = {"stream_id": stream_id, "action": action}
    result = await post_engine(f"/engine/streams/{stream_id}/{action}", payload)
    runtime = stream.runtime_state
    if runtime:
        runtime.engine_status = result.get("engine_status", runtime.engine_status)
        runtime.process_id = result.get("process_id")
        runtime.command = result.get("command")
        runtime.preview_url = result.get("preview_url")
        runtime.active_input_id = result.get("active_input_id")
        runtime.details = result.get("details", {})
        runtime.last_heartbeat_at = datetime.utcnow()
    stream.status = StreamStatus(result.get("stream_status", stream.status.value))
    db.add(StreamLogEntry(stream_id=stream_id, level="info", message=f"Engine action {action} executed"))
    db.commit()
    return EngineCommandResponse(ok=True, message=result.get("message", action), runtime=runtime)


@router.post("/{stream_id}/start", response_model=EngineCommandResponse)
async def start_stream(stream_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return await _engine_action(stream_id, "start", db)


@router.post("/{stream_id}/stop", response_model=EngineCommandResponse)
async def stop_stream(stream_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return await _engine_action(stream_id, "stop", db)


@router.post("/{stream_id}/restart", response_model=EngineCommandResponse)
async def restart_stream(stream_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return await _engine_action(stream_id, "restart", db)
