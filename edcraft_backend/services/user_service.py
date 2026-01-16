from uuid import UUID

from edcraft_backend.exceptions import DuplicateResourceError, ResourceNotFoundError
from edcraft_backend.models.user import User
from edcraft_backend.repositories.user_repository import UserRepository
from edcraft_backend.schemas.user import UserCreate, UserUpdate


class UserService:
    """Service layer for User business logic."""

    def __init__(self, user_repository: UserRepository):
        self.user_repo = user_repository

    async def create_user(self, user_data: UserCreate) -> User:
        """Create a new user.

        Args:
            user_data: User creation data

        Returns:
            Created user

        Raises:
            DuplicateResourceError: If email or username already exists
        """
        # Check for duplicates
        if await self.user_repo.email_exists(user_data.email):
            raise DuplicateResourceError("User", "email", user_data.email)

        if await self.user_repo.username_exists(user_data.username):
            raise DuplicateResourceError("User", "username", user_data.username)

        # Create user
        user = User(**user_data.model_dump())
        return await self.user_repo.create(user)

    async def list_users(self) -> list[User]:
        """List all non-deleted users.

        Returns:
            List of users ordered by creation date (newest first)
        """
        return await self.user_repo.list(
            order_by=User.created_at.desc(),
        )

    async def get_user(self, user_id: UUID) -> User:
        """Get a user by ID.

        Args:
            user_id: User UUID

        Returns:
            User entity

        Raises:
            ResourceNotFoundError: If user not found
        """
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise ResourceNotFoundError("User", str(user_id))
        return user

    async def update_user(self, user_id: UUID, user_data: UserUpdate) -> User:
        """Update a user.

        Args:
            user_id: User UUID
            user_data: User update data

        Returns:
            Updated user

        Raises:
            ResourceNotFoundError: If user not found
            DuplicateResourceError: If email or username already taken
        """
        user = await self.get_user(user_id)

        update_data = user_data.model_dump(exclude_unset=True)

        # Check for email conflict if email is being updated
        if "email" in update_data and update_data["email"] != user.email:
            if await self.user_repo.email_exists(update_data["email"], exclude_id=user_id):
                raise DuplicateResourceError("User", "email", update_data["email"])

        # Check for username conflict if username is being updated
        if "username" in update_data and update_data["username"] != user.username:
            if await self.user_repo.username_exists(update_data["username"], exclude_id=user_id):
                raise DuplicateResourceError("User", "username", update_data["username"])

        # Apply updates
        for key, value in update_data.items():
            setattr(user, key, value)

        return await self.user_repo.update(user)

    async def soft_delete_user(self, user_id: UUID) -> User:
        """Soft delete a user.

        Args:
            user_id: User UUID

        Returns:
            Soft-deleted user

        Raises:
            ResourceNotFoundError: If user not found
        """
        user = await self.get_user(user_id)
        return await self.user_repo.soft_delete(user)

    async def hard_delete_user(self, user_id: UUID) -> None:
        """Hard delete a user (cascade deletes all content).

        Args:
            user_id: User UUID

        Raises:
            ResourceNotFoundError: If user not found
        """
        user = await self.user_repo.get_by_id(user_id, include_deleted=True)
        if not user:
            raise ResourceNotFoundError("User", str(user_id))

        await self.user_repo.hard_delete(user)
