"""Repository for OAuth account operations."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from edcraft_backend.models.oauth_account import OAuthAccount


class OAuthAccountRepository:
    """Repository for OAuth account."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_provider_and_user_id(
        self, provider: str, provider_user_id: str
    ) -> OAuthAccount | None:
        """Get OAuth account by provider and provider user ID.

        Args:
            provider: OAuth provider name (e.g., 'github', 'google')
            provider_user_id: User ID from the OAuth provider

        Returns:
            OAuthAccount if found, None otherwise
        """
        stmt = select(OAuthAccount).where(
            OAuthAccount.provider == provider,
            OAuthAccount.provider_user_id == provider_user_id,
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_user_id(self, user_id: UUID) -> list[OAuthAccount]:
        """Get all OAuth accounts for a user.

        Args:
            user_id: User UUID

        Returns:
            List of OAuthAccount records
        """
        stmt = select(OAuthAccount).where(OAuthAccount.user_id == user_id)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def create(
        self, user_id: UUID, provider: str, provider_user_id: str
    ) -> OAuthAccount:
        """Create a new OAuth account link.

        Args:
            user_id: User UUID
            provider: OAuth provider name
            provider_user_id: User ID from the OAuth provider

        Returns:
            Created OAuthAccount
        """
        oauth_account = OAuthAccount(
            user_id=user_id,
            provider=provider,
            provider_user_id=provider_user_id,
        )
        self.db.add(oauth_account)
        await self.db.flush()
        await self.db.refresh(oauth_account)
        return oauth_account

    async def delete(self, oauth_account: OAuthAccount) -> None:
        """Delete an OAuth account link.

        Args:
            oauth_account: OAuthAccount to delete
        """
        await self.db.delete(oauth_account)
        await self.db.flush()
