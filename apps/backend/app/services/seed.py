from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import User
from app.security import get_password_hash


DEFAULT_ABR_PROFILES = [
    {"name": "1080p", "width": 1920, "height": 1080, "bitrate_kbps": 6000, "playlist_name": "1080p.m3u8"},
    {"name": "720p", "width": 1280, "height": 720, "bitrate_kbps": 3000, "playlist_name": "720p.m3u8"},
    {"name": "360p", "width": 640, "height": 360, "bitrate_kbps": 900, "playlist_name": "360p.m3u8"},
    {"name": "280p", "width": 480, "height": 280, "bitrate_kbps": 500, "playlist_name": "280p.m3u8"},
    {"name": "144p", "width": 256, "height": 144, "bitrate_kbps": 250, "playlist_name": "144p.m3u8"},
]


def seed_admin(db: Session) -> None:
    existing = db.query(User).filter(User.email == settings.admin_email).first()
    if existing:
        return
    db.add(User(email=settings.admin_email, password_hash=get_password_hash(settings.admin_password), is_active=True))
    db.commit()
