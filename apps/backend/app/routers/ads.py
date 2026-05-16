from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.deps import get_current_user, get_db
from app.models import AdSettings, Stream, User
from app.schemas import AdSettingsOut, AdSettingsUpdate, PlayerAdConfigOut

router = APIRouter(prefix="/ads", tags=["ads"])


def _to_player_config(settings: AdSettings, stream_key: str | None = None) -> PlayerAdConfigOut:
    return PlayerAdConfigOut(
        enabled=settings.enabled,
        provider=settings.provider,
        stream_key=stream_key,
        pre_roll=settings.pre_roll if settings.pre_roll.get("enabled") else None,
        mid_roll=settings.mid_roll if settings.mid_roll.get("enabled") else None,
        post_roll=settings.post_roll if settings.post_roll.get("enabled") else None,
        video_ad=settings.video_ad if settings.video_ad.get("enabled") else None,
        mid_roll_rules=settings.mid_roll_rules or [],
        player_hints={
            "videojs_ima": "Use videojs-ima or contrib-ads and pass the relevant VAST tag URL per slot.",
            "jwplayer": "Map enabled slots to advertising.schedule with tag and offset.",
            "shaka": "Use client-side ad insertion with IMA SDK and feed VAST URLs from this config.",
        },
    )


def _default_settings() -> AdSettings:
    return AdSettings(
        id=1,
        provider="Revive Adserver (open source)",
        enabled=False,
        pre_roll={"enabled": False, "tag_url": "", "offset": "start", "duration": "00:00:15", "skippable": False},
        mid_roll={"enabled": False, "tag_url": "", "offset": "00:10:00", "duration": "00:00:30", "skippable": False},
        post_roll={"enabled": False, "tag_url": "", "offset": "end", "duration": "00:00:15", "skippable": False},
        video_ad={"enabled": False, "tag_url": "", "offset": "manual", "duration": "00:00:20", "skippable": False},
        mid_roll_rules=["00:10:00"],
    )


def _get_or_create(db: Session) -> AdSettings:
    settings = db.query(AdSettings).filter(AdSettings.id == 1).first()
    if settings:
        return settings
    settings = _default_settings()
    db.add(settings)
    db.commit()
    db.refresh(settings)
    return settings


@router.get("", response_model=AdSettingsOut)
def get_ad_settings(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return _get_or_create(db)


@router.put("", response_model=AdSettingsOut)
def update_ad_settings(payload: AdSettingsUpdate, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    settings = _get_or_create(db)
    settings.provider = payload.provider
    settings.enabled = payload.enabled
    settings.pre_roll = payload.pre_roll.model_dump()
    settings.mid_roll = payload.mid_roll.model_dump()
    settings.post_roll = payload.post_roll.model_dump()
    settings.video_ad = payload.video_ad.model_dump()
    settings.mid_roll_rules = payload.mid_roll_rules
    settings.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(settings)
    return settings


@router.get("/player-config", response_model=PlayerAdConfigOut)
def get_player_ad_config(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    settings = _get_or_create(db)
    return _to_player_config(settings)


@router.get("/player-config/{stream_key}", response_model=PlayerAdConfigOut)
def get_stream_player_ad_config(stream_key: str, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    settings = _get_or_create(db)
    stream = db.query(Stream).filter(Stream.stream_key == stream_key).first()
    if not stream:
        return _to_player_config(settings, stream_key=stream_key)
    return _to_player_config(settings, stream_key=stream.stream_key)
