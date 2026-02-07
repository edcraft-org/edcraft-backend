"""Repository for RefreshToken model."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from edcraft_backend.models.refresh_token import RefreshToken


class RefreshTokenRepository:
    """Repository for refresh token operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get(self, token_hash: str) -> RefreshToken | None:
        """Get refresh token by its hash."""
        stmt = select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def create(
        self,
        user_id: UUID,
        token_hash: str,
        expires_at: datetime,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> RefreshToken:
        """Persist a new refresh token."""
        token = RefreshToken(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
            is_revoked=False,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        self.db.add(token)
        await self.db.flush()
        await self.db.refresh(token)
        return token

    async def revoke(self, token_id: UUID) -> None:
        """Revoke a single refresh token by ID."""
        stmt = (
            update(RefreshToken)
            .where(RefreshToken.id == token_id)
            .values(is_revoked=True)
        )
        await self.db.execute(stmt)
        await self.db.flush()

    async def revoke_all_user_tokens(self, user_id: UUID) -> None:
        """Revoke all refresh tokens for a user."""
        stmt = (
            update(RefreshToken)
            .where(RefreshToken.user_id == user_id)
            .values(is_revoked=True)
        )
        await self.db.execute(stmt)
        await self.db.flush()
