import re
from pathlib import Path
from urllib.parse import quote

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from fastapi.responses import FileResponse, PlainTextResponse, Response
from sqlalchemy.orm import Session

from app.core.config import settings
from app.deps import get_db
from app.models import Stream, User
from app.security import decode_token
from app.services.playback_auth import verify_playback_token

router = APIRouter(tags=["playback"])


def _stream_for_key(db: Session, key: str) -> Stream | None:
    if key == "main":
        return db.query(Stream).filter(Stream.is_primary.is_(True)).first()
    return db.query(Stream).filter(Stream.stream_key == key).first()


def _bearer_token(authorization: str | None) -> str | None:
    if not authorization:
        return None
    prefix = "Bearer "
    if not authorization.startswith(prefix):
        return None
    return authorization[len(prefix):].strip()


def _is_admin_token(db: Session, token: str | None) -> bool:
    if not token:
        return False
    email = decode_token(token)
    if not email:
        return False
    return db.query(User).filter(User.email == email, User.is_active.is_(True)).first() is not None


def _require_playback_access(db: Session, stream: Stream, key: str, token: str | None, authorization: str | None) -> str | None:
    if not stream.playback_auth_enabled:
        return token
    bearer = _bearer_token(authorization)
    if _is_admin_token(db, bearer):
        return token
    playback_token = token or bearer
    if playback_token and verify_playback_token(playback_token, key):
        return playback_token
    if playback_token and key == "main" and verify_playback_token(playback_token, stream.stream_key):
        return playback_token
    raise HTTPException(status_code=401, detail="Valid playback token required")


def _safe_hls_path(file_path: str) -> Path:
    root = Path(settings.hls_root).resolve()
    target = (root / file_path).resolve()
    if root not in [target, *target.parents]:
        raise HTTPException(status_code=400, detail="Invalid playback path")
    return target


def _append_token(uri: str, token: str) -> str:
    if "token=" in uri:
        return uri
    separator = "&" if "?" in uri else "?"
    return f"{uri}{separator}token={quote(token)}"


def _rewrite_manifest(content: str, token: str | None) -> str:
    if not token:
        return content

    def replace_key_uri(match: re.Match[str]) -> str:
        return f'{match.group(1)}{_append_token(match.group(2), token)}{match.group(3)}'

    content = re.sub(r'(URI=")([^"]+)(")', replace_key_uri, content)
    lines = []
    for line in content.splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            lines.append(_append_token(line, token))
        else:
            lines.append(line)
    return "\n".join(lines) + ("\n" if content.endswith("\n") else "")


@router.get("/live/{file_path:path}")
def serve_hls_file(
    file_path: str,
    request: Request,
    token: str | None = Query(default=None),
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    key = file_path.split("/", 1)[0]
    stream = _stream_for_key(db, key)
    if not stream:
        raise HTTPException(status_code=404, detail="Stream not found")
    playback_token = _require_playback_access(db, stream, key, token, authorization)

    target = _safe_hls_path(file_path)
    if not target.exists() or not target.is_file():
        raise HTTPException(status_code=404, detail="Playback file not found")

    headers = {
        "Cache-Control": "no-cache",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Headers": "Authorization, Range, Content-Type",
    }
    suffix = target.suffix.lower()
    if suffix == ".m3u8":
        content = _rewrite_manifest(target.read_text(encoding="utf-8"), playback_token)
        return PlainTextResponse(content, media_type="application/vnd.apple.mpegurl", headers=headers)
    media_type = "video/mp2t" if suffix == ".ts" else "application/octet-stream"
    return FileResponse(target, media_type=media_type, headers=headers)


@router.options("/live/{file_path:path}")
def playback_options(file_path: str):
    return Response(
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, OPTIONS",
            "Access-Control-Allow-Headers": "Authorization, Range, Content-Type",
        }
    )
