"""Mock OAuth client for testing OAuth flows without external dependencies."""

from typing import Any


class MockOAuthClient:
    """Mock OAuth client that simulates OAuth provider responses."""

    def __init__(self, provider: str = "github") -> None:
        """Initialize mock OAuth client.

        Args:
            provider: OAuth provider name (e.g., 'github')
        """
        self.provider = provider
        self.name = provider

    async def authorize_redirect(
        self, request: Any, redirect_uri: str, **kwargs: Any
    ) -> Any:
        """Mock OAuth authorization redirect.

        Args:
            request: FastAPI request object
            redirect_uri: Callback URI
            **kwargs: Additional OAuth parameters (e.g., state)

        Returns:
            Mock redirect response
        """
        from starlette.responses import RedirectResponse

        # Use provided state or generate a mock one
        state = kwargs.get("state", "mock_state")
        mock_auth_url = f"https://{self.provider}.com/authorize?redirect_uri={redirect_uri}&state={state}"
        return RedirectResponse(url=mock_auth_url, status_code=302)

    async def authorize_access_token(self, request: Any) -> dict[str, Any]:
        """Mock OAuth token exchange.

        Args:
            request: FastAPI request with authorization code

        Returns:
            Mock token response
        """
        # Simulate successful token exchange
        return {
            "access_token": "mock_access_token",
            "token_type": "bearer",
            "scope": "user:email",
        }


class MockOAuthRegistry:
    """Mock OAuth registry for testing."""

    def __init__(self) -> None:
        """Initialize mock registry."""
        self._clients: dict[str, MockOAuthClient] = {}

    def register(self, name: str, **kwargs: Any) -> None:
        """Register a mock OAuth client.

        Args:
            name: Provider name
            **kwargs: OAuth client configuration (ignored in mock)
        """
        self._clients[name] = MockOAuthClient(provider=name)

    def create_client(self, name: str) -> MockOAuthClient | None:
        """Get or create a mock OAuth client.

        Args:
            name: Provider name

        Returns:
            Mock OAuth client or None if not registered
        """
        # Return None if provider hasn't been explicitly registered
        # This simulates an unconfigured OAuth provider (503 error path)
        return self._clients.get(name)


def create_mock_oauth_user_info(
    provider: str = "github",
    provider_user_id: str = "12345",
    email: str = "oauth_user@example.com",
    name: str = "OAuth Test User",
) -> dict[str, Any]:
    """Create mock OAuth user info response.

    Args:
        provider: OAuth provider name
        provider_user_id: Unique user ID from provider
        email: User email
        name: User display name

    Returns:
        Mock user info dictionary
    """
    if provider == "github":
        return {
            "id": provider_user_id,
            "login": name.lower().replace(" ", "_"),
            "email": email,
            "name": name,
        }
    return {
        "id": provider_user_id,
        "email": email,
        "name": name,
    }
