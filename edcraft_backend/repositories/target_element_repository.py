"""Repository for TargetElement model."""

from sqlalchemy.ext.asyncio import AsyncSession

from edcraft_backend.models.target_element import TargetElement


class TargetElementRepository:
    """Repository for TargetElement operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_many(self, entities: list[TargetElement]) -> list[TargetElement]:
        """Create multiple target elements in bulk.

        Args:
            entities: List of TargetElements to create

        Returns:
            List of created target elements
        """
        self.db.add_all(entities)
        await self.db.flush()
        for entity in entities:
            await self.db.refresh(entity)
        return entities

    async def hard_delete(self, entity: TargetElement) -> None:
        """Permanently delete a target element from the database.

        Args:
            entity: TargetElement to delete
        """
        await self.db.delete(entity)
        await self.db.flush()
