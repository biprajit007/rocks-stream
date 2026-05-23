import base64
import json
from datetime import datetime, timezone
from functools import lru_cache
from typing import Any

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
    claims: set[str] = set()
    for key in ("stream", "stream_key", "sub", "aud"):
        value = payload.get(key)
        if isinstance(value, str):
            claims.add(value)
        elif isinstance(value, list):
            claims.update(str(item) for item in value)
    scope = payload.get("scope")
    if isinstance(scope, str):
        claims.update(scope.split())
    elif isinstance(scope, list):
        claims.update(str(item) for item in scope)
    return claims


def verify_playback_token(token: str, stream_key: str) -> bool:
    try:
        header_part, payload_part, signature_part = token.split(".", 2)
        header = json.loads(_b64url_decode(header_part))
        payload = json.loads(_b64url_decode(payload_part))
        if header.get("alg") != "RS256":
            return False
        signing_input = f"{header_part}.{payload_part}".encode("utf-8")
        _public_key().verify(
            _b64url_decode(signature_part),
            signing_input,
            padding.PKCS1v15(),
            hashes.SHA256(),
        )
    except (ValueError, TypeError, json.JSONDecodeError, InvalidSignature):
        return False

    now = int(datetime.now(timezone.utc).timestamp())
    exp = payload.get("exp")
    nbf = payload.get("nbf")
    if not isinstance(exp, int) or exp < now:
        return False
    if isinstance(nbf, int) and nbf > now:
        return False

    allowed = _stream_claims(payload)
    return (
        "*"
        in allowed
        or stream_key in allowed
        or "main" in allowed and stream_key == "main"
        or f"stream:{stream_key}" in allowed
        or f"play:{stream_key}" in allowed
    )
