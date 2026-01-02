"""Base repository for association/junction table models."""

from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from edcraft_backend.models.base import AssociationBase


class AssociationRepository[ModelType: AssociationBase]:
    """Base repository for association/junction table operations."""

    def __init__(self, model: type[ModelType], db: AsyncSession):
        self.model = model
        self.db = db

    async def get_by_id(
        self,
        item_id: UUID,
        eager_load: list[Any] | None = None,
    ) -> ModelType | None:
        """Get a single association by ID.

        Args:
            item_id: Association UUID
            eager_load: List of relationships to eager load

        Returns:
            Association if found, None otherwise
        """
        stmt = select(self.model).where(self.model.id == item_id)

        if eager_load:
            for relationship in eager_load:
                stmt = stmt.options(selectinload(relationship))

        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list(
        self,
        filters: dict[str, Any] | None = None,
        order_by: Any | None = None,
        limit: int | None = None,
        offset: int | None = None,
        eager_load: list[Any] | None = None,
    ) -> list[ModelType]:
        """List associations with optional filtering, pagination, and ordering.

        Args:
            filters: Dictionary of field: value filters
            order_by: SQLAlchemy order_by clause
            limit: Maximum number of results
            offset: Number of results to skip
            eager_load: List of relationships to eager load

        Returns:
            List of associations matching criteria
        """
        stmt = select(self.model)

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
        """Create a new association.

        Args:
            entity: Association to create

        Returns:
            Created association with ID and timestamp
        """
        self.db.add(entity)
        await self.db.flush()
        await self.db.refresh(entity)
        return entity

    async def update(self, entity: ModelType) -> ModelType:
        """Update an existing association.

        Args:
            entity: Association to update (must be attached to session)

        Returns:
            Updated association
        """
        await self.db.flush()
        await self.db.refresh(entity)
        return entity

    async def hard_delete(self, entity: ModelType) -> None:
        """Permanently delete an association from the database.

        Args:
            entity: Association to delete
        """
        await self.db.delete(entity)
        await self.db.flush()

    async def exists(
        self,
        item_id: UUID,
    ) -> bool:
        """Check if an association exists.

        Args:
            item_id: Association UUID

        Returns:
            True if association exists, False otherwise
        """
        stmt = select(func.count()).select_from(self.model).where(self.model.id == item_id)

        result = await self.db.execute(stmt)
        count = result.scalar_one()
        return count > 0

    async def count(
        self,
        filters: dict[str, Any] | None = None,
    ) -> int:
        """Count associations matching criteria.

        Args:
            filters: Dictionary of field: value filters

        Returns:
            Number of associations matching criteria
        """
        stmt = select(func.count()).select_from(self.model)

        if filters:
            for field, value in filters.items():
                if hasattr(self.model, field):
                    stmt = stmt.where(getattr(self.model, field) == value)

        result = await self.db.execute(stmt)
        return result.scalar_one()
