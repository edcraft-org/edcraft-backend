"""Symmetric encryption for provider API keys at rest."""

from __future__ import annotations

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken


class ProviderSecretError(Exception):
    """A stored provider secret cannot be decrypted with this installation."""


def derive_fernet_key(secret: str) -> bytes:
    """Derive a stable Fernet key from an arbitrary installation secret."""
    digest = hashlib.sha256(secret.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest)


class ProviderSecretCipher:
    """Encrypt and decrypt provider keys without exposing plaintext at rest."""

    def __init__(self, secret: str) -> None:
        if not secret.strip():
            raise ValueError("Provider encryption secret must not be blank")
        self._fernet = Fernet(derive_fernet_key(secret))

    def encrypt(self, plaintext: str) -> str:
        return self._fernet.encrypt(plaintext.encode("utf-8")).decode("ascii")

    def decrypt(self, ciphertext: str) -> str:
        try:
            return self._fernet.decrypt(ciphertext.encode("ascii")).decode("utf-8")
        except (InvalidToken, ValueError, UnicodeError) as exc:
            raise ProviderSecretError(
                "The stored provider key cannot be decrypted. "
                "Rotate the key or recreate this connection."
            ) from exc
