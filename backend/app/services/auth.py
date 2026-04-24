from __future__ import annotations
import time
from typing import Any, Dict, Optional
import bcrypt
import jwt
from app.core.config import get_settings

DEFAULT_TTL_SECONDS = 60 * 60 * 4  # 4 hours
JWT_ALG = "HS256"


class InvalidTokenError(Exception):
    """Raised when a JWT fails to decode or has expired."""

def _truncate_password(plaintext: str) -> bytes:
    return plaintext.encode("utf-8")[:72]

def hash_password(plaintext: str) -> str:
    return bcrypt.hashpw(_truncate_password(plaintext), bcrypt.gensalt(12)).decode("utf-8")

def verify_password(plaintext: str, password_hash: str) -> bool:
    if not password_hash:
        return False
    try:
        return bcrypt.checkpw(_truncate_password(plaintext), password_hash.encode("utf-8"))
    except ValueError:
        return False

def issue_token(
    subject: str,
    role: str,
    extra_claims: Optional[Dict[str, Any]] = None,
    ttl_seconds: Optional[int] = None,
) -> str:
    settings = get_settings()
    now = int(time.time())
    payload: Dict[str, Any] = {
        "sub": subject,
        "role": role,
        "iat": now,
        "exp": now + (ttl_seconds or DEFAULT_TTL_SECONDS),
    }
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, settings.secret_key, algorithm=JWT_ALG)

def decode_token(token: str) -> Dict[str, Any]:
    settings = get_settings()
    try:
        return jwt.decode(token, settings.secret_key, algorithms=[JWT_ALG])
    except jwt.ExpiredSignatureError as exc:
        raise InvalidTokenError("Token has expired.") from exc
    except jwt.InvalidTokenError as exc:
        raise InvalidTokenError(str(exc)) from exc