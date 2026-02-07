"""OAuth provider-specific handlers for fetching user information."""

from __future__ import annotations

from typing import Any

from authlib.integrations.base_client import OAuthError
from authlib.integrations.starlette_client import StarletteOAuth2App
from pydantic import BaseModel

from edcraft_backend.exceptions import AuthenticationError
from edcraft_backend.oauth.config import OAuthProvider


class OAuthUserInfo(BaseModel):
    """Standardized OAuth user information."""

    provider_user_id: str
    email: str
    username: str


async def fetch_github_user_info(
    client: StarletteOAuth2App, token: dict
) -> OAuthUserInfo:
    """Fetch user information from GitHub.

    Args:
        client: Authlib OAuth client
        token: OAuth token dictionary from authorize_access_token

    Returns:
        OAuthUserInfo with user data

    Raises:
        AuthenticationError: If user data cannot be fetched or is invalid
    """
    try:
        # Fetch user profile
        user_response = await client.get("user", token=token)
        user_response.raise_for_status()
        user_data = user_response.json()

        # Fetch user emails
        emails_response = await client.get("user/emails", token=token)
        emails_response.raise_for_status()
        emails = emails_response.json()

    except OAuthError as e:
        raise AuthenticationError(f"Failed to fetch GitHub user data: {e}") from e
    except (ValueError, KeyError) as e:
        raise AuthenticationError(f"Invalid response from GitHub API: {e}") from e

    # Extract and validate data
    provider_user_id = str(user_data.get("id", ""))
    if not provider_user_id:
        raise AuthenticationError("GitHub user ID missing from response")

    username = user_data.get("login", "")
    if not username:
        raise AuthenticationError("GitHub username missing from response")

    email = _extract_verified_email(emails)

    return OAuthUserInfo(
        provider_user_id=provider_user_id,
        email=email,
        username=username,
    )


def _extract_verified_email(emails: list[dict[str, Any]]) -> str:
    """Extract a verified email from GitHub emails response.

    Prefers primary verified email, falls back to any verified email.

    Args:
        emails: List of email objects from GitHub /user/emails endpoint

    Returns:
        Verified email address

    Raises:
        AuthenticationError: If no verified email is found
    """
    if not emails or not isinstance(emails, list):
        raise AuthenticationError("No emails returned from GitHub")

    # Try to find primary verified email first
    for email_obj in emails:
        if (
            email_obj.get("primary")
            and email_obj.get("verified")
            and email_obj.get("email")
        ):
            return str(email_obj["email"])

    # Fallback to any verified email
    for email_obj in emails:
        if email_obj.get("verified") and email_obj.get("email"):
            return str(email_obj["email"])

    # No verified email found
    raise AuthenticationError(
        "No verified email found in GitHub account. Please verify an email address."
    )


# Map provider names to their handler functions
PROVIDER_HANDLERS = {
    OAuthProvider.GITHUB: fetch_github_user_info,
}
