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
from app.services.aes_key_store import current_key, get_key, key_url

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
    """
    Enforce playback auth when stream.playback_auth_enabled is True.
    Returns the playback token if access is granted (used for manifest rewriting),
    or None if auth is disabled.
    Raises HTTP 401 if auth is required but the token is invalid/missing.
    """
    if not stream.playback_auth_enabled:
        return token

    bearer = _bearer_token(authorization)

    # Admin JWT always passes
    if _is_admin_token(db, bearer):
        return token

    # Try playback JWT (RS256 signed by client with matching private key)
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


def _inject_aes_key_tag(content: str, stream_key: str) -> str:
    """
    Inject (or replace) the #EXT-X-KEY tag in an HLS variant playlist
    with the current AES-128 rotating key.
    """
    kid, _ = current_key()
    enc_url = key_url(kid)
    # Build IV from kid for determinism (16 hex bytes, zero-padded)
    iv_hex = "0x" + kid.ljust(32, "0")
    key_tag = f'#EXT-X-KEY:METHOD=AES-128,URI="{enc_url}",IV={iv_hex}'

    lines = content.splitlines()
    new_lines = []
    replaced = False
    for line in lines:
        if line.startswith("#EXT-X-KEY:"):
            if not replaced:
                new_lines.append(key_tag)
                replaced = True
            # drop old duplicate key tags
            continue
        new_lines.append(line)

    if not replaced:
        # Insert after #EXTM3U header line
        insert_at = 1 if new_lines and new_lines[0].startswith("#EXTM3U") else 0
        new_lines.insert(insert_at, key_tag)

    return "\n".join(new_lines) + ("\n" if content.endswith("\n") else "")


def _rewrite_manifest(content: str, token: str | None, stream_key: str = "", is_variant: bool = False) -> str:
    """
    Rewrite an HLS manifest:
      - Append ?token= to all segment/sub-manifest URIs (for auth'd streams)
      - Inject AES-128 key tag into variant playlists
    """
    if is_variant:
        content = _inject_aes_key_tag(content, stream_key)

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
    """
    Serve the raw 16-byte AES-128 key for a given key ID.
    Requires the same playback token as the HLS manifest.
    The HLS player fetches this automatically via the #EXT-X-KEY URI.
    """
    bearer = _bearer_token(authorization)
    playback_token = token or bearer

    # Must present a valid playback JWT or admin JWT
    if not playback_token:
        raise HTTPException(status_code=401, detail="Playback token required for AES key")

    # Accept admin JWT
    if not _is_admin_token(db, playback_token):
        # Try playback JWT — wildcard "*" accepted (no specific stream check needed here)
        from app.services.playback_auth import verify_playback_token as _vpt
        if not _vpt(playback_token, "*") and not _vpt(playback_token, "main"):
            # Try any stream key match (broad check — key endpoint doesn't know stream)
            # We just verify the JWT signature + expiry, stream claim check is relaxed
            from app.services.playback_auth import _b64url_decode, _public_key
            import json, base64
            from cryptography.hazmat.primitives import hashes, serialization
            from cryptography.hazmat.primitives.asymmetric import padding
            from cryptography.exceptions import InvalidSignature
            from datetime import datetime, timezone
            try:
                parts = playback_token.split(".", 2)
                if len(parts) != 3:
                    raise ValueError("bad token")
                header_part, payload_part, sig_part = parts
                header = json.loads(_b64url_decode(header_part))
                payload = json.loads(_b64url_decode(payload_part))
                if header.get("alg") != "RS256":
                    raise ValueError("bad alg")
                signing_input = f"{header_part}.{payload_part}".encode()
                _public_key().verify(
                    _b64url_decode(sig_part),
                    signing_input,
                    padding.PKCS1v15(),
                    hashes.SHA256(),
                )
                now = int(datetime.now(timezone.utc).timestamp())
                exp = payload.get("exp")
                if not isinstance(exp, int) or exp < now:
                    raise ValueError("expired")
            except Exception:
                raise HTTPException(status_code=401, detail="Invalid playback token")

    key_bytes = get_key(kid)
    if key_bytes is None:
        raise HTTPException(status_code=404, detail="AES key not found or expired")

    return Response(
        content=key_bytes,
        media_type="application/octet-stream",
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Authorization",
        },
    )


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
        content = target.read_text(encoding="utf-8")
        # Variant playlist (has #EXTINF segments) — inject AES key + rewrite URIs
        is_variant = "#EXTINF" in content
        content = _rewrite_manifest(content, playback_token, stream_key=key, is_variant=is_variant)
        return PlainTextResponse(
            content,
            media_type="application/vnd.apple.mpegurl",
            headers=headers,
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
