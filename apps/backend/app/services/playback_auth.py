import base64
import json
from datetime import datetime, timezone
from functools import lru_cache
from typing import Any, Optional

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

from app.core.config import settings


def _b64url_decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


@lru_cache(maxsize=1)
def _public_key():
    raw_key = settings.playback_token_public_key.strip().encode("utf-8")
    if raw_key.startswith(b"-----BEGIN"):
        return serialization.load_pem_public_key(raw_key)
    return serialization.load_ssh_public_key(raw_key)


def _stream_claims(payload: dict[str, Any]) -> set[str]:
    """
    Extract all string stream identifiers from the token payload.
    Handles:
      - stream_key: "tv1"
      - stream: "tv1"
      - sub: "tv1" or 1 (ignored if int — sub as int is a user id)
      - aud: "tv1" or ["tv1"]
      - scope: "tv1 tv2" or ["tv1"]
      - stream_id: 334  (numeric DB id — matched separately in verify_playback_token)
    """
    claims: set[str] = set()
    for key in ("stream", "stream_key", "aud"):
        value = payload.get(key)
        if isinstance(value, str):
            claims.add(value)
        elif isinstance(value, list):
            claims.update(str(item) for item in value)

    # sub: only use as stream claim if it's a string
    sub = payload.get("sub")
    if isinstance(sub, str):
        claims.add(sub)

    scope = payload.get("scope")
    if isinstance(scope, str):
        claims.update(scope.split())
    elif isinstance(scope, list):
        claims.update(str(item) for item in scope)

    return claims


def _verify_signature_and_expiry(token: str) -> Optional[dict]:
    """
    Verify RS256 signature + exp/nbf. Returns payload dict on success, None on failure.
    """
    try:
        header_part, payload_part, signature_part = token.split(".", 2)
        header = json.loads(_b64url_decode(header_part))
        payload = json.loads(_b64url_decode(payload_part))
        if header.get("alg") != "RS256":
            return None
        signing_input = f"{header_part}.{payload_part}".encode("utf-8")
        _public_key().verify(
            _b64url_decode(signature_part),
            signing_input,
            padding.PKCS1v15(),
            hashes.SHA256(),
        )
    except (ValueError, TypeError, json.JSONDecodeError, InvalidSignature):
        return None

    now = int(datetime.now(timezone.utc).timestamp())
    exp = payload.get("exp")
    nbf = payload.get("nbf")
    if not isinstance(exp, int) or exp < now:
        return None
    if isinstance(nbf, int) and nbf > now:
        return None

    return payload


def verify_playback_token(token: str, stream_key: str) -> bool:
    """
    Verify a playback JWT for a given stream_key.

    Accepts tokens where any of these match stream_key:
      - payload.stream_key == stream_key
      - payload.stream == stream_key
      - payload.sub == stream_key  (string only)
      - payload.aud contains stream_key
      - payload.scope contains stream_key
      - "*" wildcard in any of the above
      - payload.stream_id matches DB id for this stream_key (looked up lazily)
    """
    payload = _verify_signature_and_expiry(token)
    if payload is None:
        return False

    # Wildcard — any stream allowed
    allowed = _stream_claims(payload)
    if "*" in allowed:
        return True

    # Direct stream key match
    if stream_key in allowed:
        return True

    # "main" alias
    if "main" in allowed and stream_key == "main":
        return True

    # Prefixed claims
    if f"stream:{stream_key}" in allowed or f"play:{stream_key}" in allowed:
        return True

    # Numeric stream_id — look up stream key from DB
    stream_id = payload.get("stream_id")
    if isinstance(stream_id, int):
        try:
            from app.db import SessionLocal
            from app.models import Stream
            db = SessionLocal()
            try:
                stream = db.query(Stream).filter(Stream.id == stream_id).first()
                if stream and (stream.stream_key == stream_key or stream_key == "main" and stream.is_primary):
                    return True
            finally:
                db.close()
        except Exception:
            pass

    return False


def verify_playback_token_any_stream(token: str) -> bool:
    """
    Verify a playback JWT without checking a specific stream key.
    Used by the AES key endpoint — just validates signature + expiry.
    """
    return _verify_signature_and_expiry(token) is not None
