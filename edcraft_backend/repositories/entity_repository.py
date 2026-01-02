"""Base repository for entity models."""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from edcraft_backend.models.base import EntityBase


class EntityRepository[ModelType: EntityBase]:
    """Base repository with generic CRUD operations for entity models."""

    def __init__(self, model: type[ModelType], db: AsyncSession):
        self.model = model
        self.db = db

    async def get_by_id(
        self,
        item_id: UUID,
        include_deleted: bool = False,
        eager_load: list[Any] | None = None,
    ) -> ModelType | None:
        """Get a single entity by ID.

        Args:
            item_id: Entity UUID
            include_deleted: Whether to include soft-deleted entities
            eager_load: List of relationships to eager load

        Returns:
            Entity if found, None otherwise
        """
        stmt = select(self.model).where(self.model.id == item_id)

        if not include_deleted:
            stmt = stmt.where(self.model.deleted_at.is_(None))

        if eager_load:
            for relationship in eager_load:
                stmt = stmt.options(selectinload(relationship))

        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list(
        self,
        filters: dict[str, Any] | None = None,
        include_deleted: bool = False,
        order_by: Any | None = None,
        limit: int | None = None,
        offset: int | None = None,
        eager_load: list[Any] | None = None,
    ) -> list[ModelType]:
        """List entities with optional filtering, pagination, and ordering.

        Args:
            filters: Dictionary of field: value filters
            include_deleted: Whether to include soft-deleted entities
            order_by: SQLAlchemy order_by clause
            limit: Maximum number of results
            offset: Number of results to skip
            eager_load: List of relationships to eager load

        Returns:
            List of entities matching criteria
        """
        stmt = select(self.model)

        if not include_deleted:
            stmt = stmt.where(self.model.deleted_at.is_(None))

        if filters:
            for field, value in filters.items():
                if hasattr(self.model, field):
                    stmt = stmt.where(getattr(self.model, field) == value)

        if order_by is not None:
            stmt = stmt.order_by(order_by)

        if eager_load:
            for relationship in eager_load:
                stmt = stmt.options(selectinload(relationship))

        if offset:
            stmt = stmt.offset(offset)

        if limit:
            stmt = stmt.limit(limit)

        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def create(self, entity: ModelType) -> ModelType:
        """Create a new entity.

        Args:
            entity: Entity to create

        Returns:
            Created entity with ID and timestamps
        """
        self.db.add(entity)
        await self.db.flush()
        await self.db.refresh(entity)
        return entity

    async def update(self, entity: ModelType) -> ModelType:
        """Update an existing entity.

        Args:
            entity: Entity to update (must be attached to session)

        Returns:
            Updated entity
        """
        entity.updated_at = datetime.now(UTC)
        await self.db.flush()
        await self.db.refresh(entity)
        return entity

    async def soft_delete(self, entity: ModelType) -> ModelType:
        """Soft delete an entity by setting deleted_at timestamp.

        Args:
            entity: Entity to soft delete

        Returns:
            Soft-deleted entity
        """
        entity.deleted_at = datetime.now(UTC)
        await self.db.flush()
        await self.db.refresh(entity)
        return entity

    async def hard_delete(self, entity: ModelType) -> None:
        """Permanently delete an entity from the database.

        Args:
            entity: Entity to delete
        """
        await self.db.delete(entity)
        await self.db.flush()

    async def exists(
        self,
        item_id: UUID,
        include_deleted: bool = False,
    ) -> bool:
        """Check if an entity exists.

        Args:
            item_id: Entity UUID
            include_deleted: Whether to include soft-deleted entities

        Returns:
            True if entity exists, False otherwise
        """
        stmt = (
            select(func.count()).select_from(self.model).where(self.model.id == item_id)
        )

        if not include_deleted:
            stmt = stmt.where(self.model.deleted_at.is_(None))

        result = await self.db.execute(stmt)
        count = result.scalar_one()
        return count > 0

    async def count(
        self,
        filters: dict[str, Any] | None = None,
        include_deleted: bool = False,
    ) -> int:
        """Count entities matching criteria.

        Args:
            filters: Dictionary of field: value filters
            include_deleted: Whether to include soft-deleted entities

        Returns:
            Number of entities matching criteria
        """
        stmt = select(func.count()).select_from(self.model)

        if not include_deleted:
            stmt = stmt.where(self.model.deleted_at.is_(None))

        if filters:
            for field, value in filters.items():
                if hasattr(self.model, field):
                    stmt = stmt.where(getattr(self.model, field) == value)

        result = await self.db.execute(stmt)
        return result.scalar_one()
