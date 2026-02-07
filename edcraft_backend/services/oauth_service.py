"""OAuth service for handling OAuth authentication flows."""

from __future__ import annotations

from typing import TYPE_CHECKING

from edcraft_backend.exceptions import AuthenticationError
from edcraft_backend.models.user import User
from edcraft_backend.repositories.oauth_account_repository import OAuthAccountRepository
from edcraft_backend.repositories.user_repository import UserRepository
from edcraft_backend.schemas.auth import TokenPairResponse

if TYPE_CHECKING:
    from edcraft_backend.services.auth_service import AuthService
    from edcraft_backend.services.folder_service import FolderService


class OAuthService:
    """Handles OAuth authentication flows."""

    def __init__(
        self,
        user_repo: UserRepository,
        oauth_account_repo: OAuthAccountRepository,
        auth_svc: AuthService,
        folder_svc: FolderService,
    ):
        self.user_repo = user_repo
        self.oauth_account_repo = oauth_account_repo
        self.auth_svc = auth_svc
        self.folder_svc = folder_svc

    async def handle_oauth_callback(
        self,
        provider: str,
        provider_user_id: str,
        email: str,
        name: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> TokenPairResponse:
        """Handle OAuth callback and return tokens."""
        # Check if OAuth account already exists
        oauth_account = await self.oauth_account_repo.get_by_provider_and_user_id(
            provider, provider_user_id
        )

        if oauth_account:
            # Existing OAuth link - get the user
            user = await self.user_repo.get_by_id(oauth_account.user_id)
            if not user or not user.is_active:
                raise AuthenticationError()
        else:
            # No existing OAuth link - check if user exists by email
            user = await self.user_repo.get_by_email(email)

            if user:
                # User exists - link OAuth account to existing user
                await self.oauth_account_repo.create(
                    user_id=user.id,
                    provider=provider,
                    provider_user_id=provider_user_id,
                )
            else:
                # New user - create account
                user = await self._create_oauth_user(
                    email=email,
                    name=name or self._generate_name_from_email(email),
                    provider=provider,
                    provider_user_id=provider_user_id,
                )

        # Issue tokens
        return await self.auth_svc.issue_tokens(user.id, ip_address, user_agent)

    async def _create_oauth_user(
        self, email: str, name: str, provider: str, provider_user_id: str
    ) -> User:
        # Create user
        user = User(
            email=email,
            name=name,
            password_hash=None,  # OAuth users don't have passwords
            is_active=True,
        )
        user = await self.user_repo.create(user)

        # Create root folder for user
        await self.folder_svc.create_root_folder(user.id)

        # Link OAuth account
        await self.oauth_account_repo.create(
            user_id=user.id,
            provider=provider,
            provider_user_id=provider_user_id,
        )

        return user

    def _generate_name_from_email(self, email: str) -> str:
        """Generate a name from email address."""
        local_part = email.split("@")[0]
        return local_part.lower()
