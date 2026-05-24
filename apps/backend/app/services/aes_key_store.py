"""
AES-128 rotating key store for HLS encryption.

- Generates a new 16-byte AES-128 key every KEY_ROTATION_SECONDS (default 180s / 3 min).
- Keeps the previous key alive for one extra window so in-flight segments still decrypt.
- Exposes:
    current_key()  -> (key_id: str, key_bytes: bytes)
    get_key(kid)   -> bytes | None
    key_url(kid)   -> str   (absolute URL clients use in #EXT-X-KEY)
"""

import os
import secrets
import time
import threading
from typing import Optional

from app.core.config import settings

KEY_ROTATION_SECONDS: int = int(os.getenv("AES_KEY_ROTATION_SECONDS", "180"))

_lock = threading.Lock()
_keys: dict[str, bytes] = {}        # kid -> raw 16 bytes
_current_kid: str = ""
_next_rotation: float = 0.0


def _new_kid() -> str:
    return secrets.token_hex(8)


def _rotate() -> None:
    global _current_kid, _next_rotation, _keys
    new_kid = _new_kid()
    new_key = secrets.token_bytes(16)  # AES-128 = 16 bytes

    # Keep only current + new (drop older ones)
    old_kid = _current_kid
    _keys = {k: v for k, v in _keys.items() if k == old_kid}
    _keys[new_kid] = new_key

    _current_kid = new_kid
    _next_rotation = time.monotonic() + KEY_ROTATION_SECONDS


def _ensure_initialised() -> None:
    global _next_rotation
    if not _current_kid:
        _rotate()


def current_key() -> tuple[str, bytes]:
    """Return (kid, key_bytes) for the active encryption key, rotating if due."""
    with _lock:
        _ensure_initialised()
        if time.monotonic() >= _next_rotation:
            _rotate()
        return _current_kid, _keys[_current_kid]


def get_key(kid: str) -> Optional[bytes]:
    """Return raw key bytes for a given kid, or None if unknown/expired."""
    with _lock:
        _ensure_initialised()
        if time.monotonic() >= _next_rotation:
            _rotate()
        return _keys.get(kid)


def key_url(kid: str) -> str:
    """Absolute URL the HLS client will fetch to retrieve the AES key."""
    return f"{settings.public_scheme}://{settings.public_domain}/api/v1/playback/aes-key/{kid}"
