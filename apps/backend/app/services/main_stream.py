import os

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import Stream


def sync_main_stream_alias(db: Session) -> None:
    main_alias = os.path.join(settings.hls_root, "main")
    primary = db.query(Stream).filter(Stream.is_primary.is_(True)).order_by(Stream.updated_at.desc()).first()

    if os.path.lexists(main_alias):
        if os.path.isdir(main_alias) and not os.path.islink(main_alias):
            for root, dirs, files in os.walk(main_alias, topdown=False):
                for name in files:
                    os.remove(os.path.join(root, name))
                for name in dirs:
                    os.rmdir(os.path.join(root, name))
            os.rmdir(main_alias)
        else:
            os.unlink(main_alias)

    if not primary:
        return

    target_dir = os.path.join(settings.hls_root, primary.stream_key)
    os.makedirs(target_dir, exist_ok=True)
    os.symlink(target_dir, main_alias)
