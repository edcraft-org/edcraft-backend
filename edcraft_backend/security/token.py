"""JWT token creation, decoding, and hashing."""

import hashlib
import secrets
from datetime import datetime, timedelta

from jose import JWTError, jwt

from edcraft_backend.config import settings
from edcraft_backend.exceptions import TokenDecodeError


def hash_token(token: str) -> str:
    """SHA-256 hash of a raw token."""
    return hashlib.sha256(token.encode()).hexdigest()


def generate_token(length: int = 32) -> str:
    """Generate a cryptographically secure random token."""
    return secrets.token_urlsafe(length)


def create_access_token(sub: str, now: datetime) -> str:
    """Create a short-lived JWT access token."""
    payload = {
        "sub": sub,
        "type": "access",
        "iat": int(now.timestamp()),
        "exp": int(
            (
                now + timedelta(minutes=settings.jwt.access_token_expire_minutes)
            ).timestamp()
        ),
        "iss": settings.jwt.issuer,
        "aud": settings.jwt.audience,
    }
    return jwt.encode(
        payload,
        settings.jwt.secret,
        algorithm=settings.jwt.algorithm,
        headers={"kid": settings.jwt.kid},
    )


def create_refresh_token(sub: str, now: datetime) -> str:
    """Create a long-lived JWT refresh token."""
    payload = {
        "sub": sub,
        "type": "refresh",
        "iat": int(now.timestamp()),
        "exp": int(
            (now + timedelta(days=settings.jwt.refresh_token_expire_days)).timestamp()
        ),
        "iss": settings.jwt.issuer,
        "aud": settings.jwt.audience,
    }
    return jwt.encode(
        payload,
        settings.jwt.secret,
        algorithm=settings.jwt.algorithm,
        headers={"kid": settings.jwt.kid},
    )


def decode_token(token: str) -> dict:
    """Decode and validate a JWT. Raises InvalidTokenError on failure."""
    try:
        return jwt.decode(
            token,
            settings.jwt.secret,
            algorithms=[settings.jwt.algorithm],
            audience=settings.jwt.audience,
            issuer=settings.jwt.issuer,
        )
    except JWTError as e:
        raise TokenDecodeError() from e
