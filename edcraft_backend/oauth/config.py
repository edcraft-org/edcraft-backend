"""OAuth provider configuration."""

from enum import Enum


class OAuthProvider(str, Enum):
    """Supported OAuth providers."""

    GITHUB = "github"


SUPPORTED_PROVIDERS = {provider.value for provider in OAuthProvider}
