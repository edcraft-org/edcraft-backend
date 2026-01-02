from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from edcraft_backend.models.user import User
from edcraft_backend.repositories.base import EntityRepository


class UserRepository(EntityRepository[User]):
    """Repository for User entity operations."""

    def __init__(self, db: AsyncSession):
        super().__init__(User, db)

    async def get_by_email(
        self,
        email: str,
        include_deleted: bool = False,
    ) -> User | None:
        """Get user by email address.

        Args:
            email: User's email address
            include_deleted: Whether to include soft-deleted users

        Returns:
            User if found, None otherwise
        """
        stmt = select(User).where(User.email == email)

        if not include_deleted:
            stmt = stmt.where(User.deleted_at.is_(None))

        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_username(
        self,
        username: str,
        include_deleted: bool = False,
    ) -> User | None:
        """Get user by username.

        Args:
            username: User's username
            include_deleted: Whether to include soft-deleted users

        Returns:
            User if found, None otherwise
        """
        stmt = select(User).where(User.username == username)

        if not include_deleted:
            stmt = stmt.where(User.deleted_at.is_(None))

        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def email_exists(
        self,
        email: str,
        exclude_id: UUID | None = None,
        include_deleted: bool = False,
    ) -> bool:
        """Check if email is already taken.

        Args:
            email: Email to check
            exclude_id: Optional user ID to exclude from check (for updates)
            include_deleted: Whether to include soft-deleted users

        Returns:
            True if email exists, False otherwise
        """
        stmt = select(User).where(User.email == email)

        if exclude_id:
            stmt = stmt.where(User.id != exclude_id)

        if not include_deleted:
            stmt = stmt.where(User.deleted_at.is_(None))

        result = await self.db.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def username_exists(
        self,
        username: str,
        exclude_id: UUID | None = None,
        include_deleted: bool = False,
    ) -> bool:
        """Check if username is already taken.

        Args:
            username: Username to check
            exclude_id: Optional user ID to exclude from check (for updates)
            include_deleted: Whether to include soft-deleted users

        Returns:
            True if username exists, False otherwise
        """
        stmt = select(User).where(User.username == username)

        if exclude_id:
            stmt = stmt.where(User.id != exclude_id)

        if not include_deleted:
            stmt = stmt.where(User.deleted_at.is_(None))

        result = await self.db.execute(stmt)
        return result.scalar_one_or_none() is not None
