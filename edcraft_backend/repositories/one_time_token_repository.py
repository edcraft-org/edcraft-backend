"""Repository for OneTimeToken model."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from edcraft_backend.models.one_time_token import OneTimeToken, TokenType


class OneTimeTokenRepository:
    """Repository for one-time token operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_token_hash(
        self, token_hash: str, token_type: TokenType
    ) -> OneTimeToken | None:
        """Get token by hash and type."""
        stmt = select(OneTimeToken).where(
            OneTimeToken.token_hash == token_hash,
            OneTimeToken.token_type == token_type,
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def create(
        self,
        user_id: UUID,
        token_hash: str,
        token_type: TokenType,
        expires_at: datetime,
    ) -> OneTimeToken:
        """Create a new one-time token."""
        token = OneTimeToken(
            user_id=user_id,
            token_hash=token_hash,
            token_type=token_type,
            expires_at=expires_at,
            is_used=False,
        )
        self.db.add(token)
        await self.db.flush()
        await self.db.refresh(token)
        return token

    async def mark_as_used(self, token_id: UUID) -> None:
        """Mark token as used."""
        stmt = (
            update(OneTimeToken).where(OneTimeToken.id == token_id).values(is_used=True)
        )
        await self.db.execute(stmt)
        await self.db.flush()

    async def revoke_all_user_tokens(
        self, user_id: UUID, token_type: TokenType
    ) -> None:
        """Revoke all tokens of a specific type for a user."""
        stmt = (
            update(OneTimeToken)
            .where(
                OneTimeToken.user_id == user_id,
                OneTimeToken.token_type == token_type,
            )
            .values(is_used=True)
        )
        await self.db.execute(stmt)
        await self.db.flush()
