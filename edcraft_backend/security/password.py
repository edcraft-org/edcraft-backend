"""Password hashing with Argon2."""

from argon2 import PasswordHasher

from edcraft_backend.config import get_settings

_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    """Hash a plaintext password using Argon2."""
    min_length = get_settings().password_min_length
    if len(password) < min_length:
        raise ValueError(f"Password must be at least {min_length} characters")
    return _hasher.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    """Verify a plaintext password against an Argon2 hash."""
    try:
        return _hasher.verify(hashed, plain)
    except Exception:
        return False


def needs_rehash(password_hash: str) -> bool:
    """Check whether a hash was created with outdated Argon2 parameters."""
    try:
        return _hasher.check_needs_rehash(password_hash)
    except Exception:
        return True
