"""OAuth client configuration using Authlib."""

from authlib.integrations.starlette_client import OAuth

from edcraft_backend.config import settings
from edcraft_backend.oauth.config import OAuthProvider

# Initialize OAuth registry
oauth = OAuth()

# Register GitHub OAuth provider
oauth.register(
    name=OAuthProvider.GITHUB,
    client_id=settings.oauth_github.client_id,
    client_secret=settings.oauth_github.client_secret,
    access_token_url="https://github.com/login/oauth/access_token", # noqa S106
    access_token_params=None,
    authorize_url="https://github.com/login/oauth/authorize",
    authorize_params=None,
    api_base_url="https://api.github.com/",
    client_kwargs={"scope": "user:email"},
)
