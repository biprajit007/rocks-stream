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
from app.services.playback_auth import verify_playback_token, verify_playback_token_any_stream
from app.services.aes_key_store import current_key, get_key, key_url


def _aes_encrypt_segment(data: bytes, kid: str) -> bytes:
    """Encrypt raw MPEG-TS segment bytes with AES-128-CBC using the key for kid."""
    from Crypto.Cipher import AES
    from Crypto.Util.Padding import pad
    key_bytes = get_key(kid)
    if key_bytes is None:
        raise HTTPException(status_code=503, detail="AES key expired, retry")
    iv_bytes = int(kid.rjust(32, "0"), 16).to_bytes(16, "big")
    cipher = AES.new(key_bytes, AES.MODE_CBC, iv_bytes)
    return cipher.encrypt(pad(data, AES.block_size))


router = APIRouter(tags=["playback"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

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


def _require_playback_access(
    db: Session,
    stream: Stream,
    key: str,
    token: str | None,
    authorization: str | None,
) -> str | None:
    if not stream.playback_auth_enabled:
        return token

    bearer = _bearer_token(authorization)

    # Admin JWT always passes
    if _is_admin_token(db, bearer):
        return token

    # Try playback JWT (RS256)
    playback_token = token or bearer
    if playback_token and (verify_playback_token(playback_token, key) or verify_playback_token_any_stream(playback_token)):
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


def _append_param(uri: str, key: str, value: str) -> str:
    separator = "&" if "?" in uri else "?"
    return f"{uri}{separator}{key}={quote(value)}"


def _inject_aes_key_tag(content: str, stream_key: str) -> tuple[str, str]:
    """Inject #EXT-X-KEY tag and return (modified_content, current_kid)."""
    kid, _ = current_key()
    enc_url = key_url(kid)
    iv_hex = "0x" + kid.rjust(32, "0")
    key_tag = f'#EXT-X-KEY:METHOD=AES-128,URI="{enc_url}",IV={iv_hex}'

    lines = content.splitlines()
    new_lines = []
    replaced = False
    for line in lines:
        if line.startswith("#EXT-X-KEY:"):
            if not replaced:
                new_lines.append(key_tag)
                replaced = True
            continue
        new_lines.append(line)

    if not replaced:
        insert_at = 1 if new_lines and new_lines[0].startswith("#EXTM3U") else 0
        new_lines.insert(insert_at, key_tag)

    result = "\n".join(new_lines) + ("\n" if content.endswith("\n") else "")
    return result, kid


def _rewrite_manifest(content: str, token: str | None, stream_key: str = "", is_variant: bool = False) -> str:
    current_kid: str | None = None

    if is_variant:
        content, current_kid = _inject_aes_key_tag(content, stream_key)

    if not token:
        return content

    # Append token + kid to key URI
    def replace_key_uri(match: re.Match[str]) -> str:
        uri = match.group(2)
        if "token=" not in uri:
            uri = _append_param(uri, "token", token)
        return f'{match.group(1)}{uri}{match.group(3)}'

    content = re.sub(r'(URI=")([^"]+)(")', replace_key_uri, content)

    # Append token + kid to every segment line so backend knows which key to encrypt with
    lines = []
    for line in content.splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            # Add token
            if "token=" not in line:
                line = _append_param(line, "token", token)
            # Add kid so encryption uses the same key as the manifest's EXT-X-KEY
            if current_kid and "kid=" not in line:
                line = _append_param(line, "kid", current_kid)
            lines.append(line)
        else:
            lines.append(line)
    return "\n".join(lines) + ("\n" if content.endswith("\n") else "")


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("/api/v1/playback/aes-key/{kid}")
def serve_aes_key(
    kid: str,
    token: str | None = Query(default=None),
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    bearer = _bearer_token(authorization)
    playback_token = token or bearer

    if not playback_token:
        raise HTTPException(status_code=401, detail="Playback token required for AES key")

    if not _is_admin_token(db, playback_token):
        if not verify_playback_token_any_stream(playback_token):
            raise HTTPException(status_code=401, detail="Invalid playback token")

    key_bytes = get_key(kid)
    if key_bytes is None:
        raise HTTPException(status_code=404, detail="AES key not found or expired")

    return Response(
        content=key_bytes,
        media_type="application/octet-stream",
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate",
        },
    )


@router.get("/live/{file_path:path}")
def serve_hls_file(
    file_path: str,
    request: Request,
    token: str | None = Query(default=None),
    kid: str | None = Query(default=None),
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    stream_key = file_path.split("/", 1)[0]
    stream = _stream_for_key(db, stream_key)
    if not stream:
        raise HTTPException(status_code=404, detail="Stream not found")

    playback_token = _require_playback_access(db, stream, stream_key, token, authorization)

    target = _safe_hls_path(file_path)
    if not target.exists() or not target.is_file():
        raise HTTPException(status_code=404, detail="Playback file not found")

    headers = {
        "Cache-Control": "no-cache",
    }

    suffix = target.suffix.lower()
    if suffix == ".m3u8":
        content = target.read_text(encoding="utf-8")
        is_variant = "#EXTINF" in content
        content = _rewrite_manifest(
            content,
            playback_token,
            stream_key=stream_key,
            is_variant=is_variant and stream.playback_auth_enabled,
        )
        return PlainTextResponse(
            content,
            media_type="application/vnd.apple.mpegurl",
            headers=headers,
        )

    if suffix == ".ts" and stream.playback_auth_enabled:
        # Use the kid from the query param (set when manifest was built) so
        # encryption always matches what the player's EXT-X-KEY tag says.
        # Fall back to current key only if no kid param (e.g. direct access).
        encrypt_kid = kid if kid else current_key()[0]
        raw = target.read_bytes()
        encrypted = _aes_encrypt_segment(raw, encrypt_kid)
        return Response(
            content=encrypted,
            media_type="video/mp2t",
            headers={**headers, "Content-Length": str(len(encrypted))},
        )

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


@router.options("/api/v1/playback/aes-key/{kid}")
def aes_key_options(kid: str):
    return Response(
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, OPTIONS",
            "Access-Control-Allow-Headers": "Authorization",
        }
    )
