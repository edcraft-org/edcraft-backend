"""OAuth provider configuration."""

from enum import StrEnum


class OAuthProvider(StrEnum):
    """Supported OAuth providers."""

    GITHUB = "github"


SUPPORTED_PROVIDERS = {provider.value for provider in OAuthProvider}
