"""Repository for ResourceCollaborator association operations."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from edcraft_backend.models.assessment_question import AssessmentQuestion
from edcraft_backend.models.enums import CollaboratorRole, ResourceType
from edcraft_backend.models.resource_collaborator import ResourceCollaborator
from edcraft_backend.repositories.base import AssociationRepository


class ResourceCollaboratorRepository(AssociationRepository[ResourceCollaborator]):
    """Repository for ResourceCollaborator association operations."""

    def __init__(self, db: AsyncSession):
        super().__init__(ResourceCollaborator, db)

    async def find_by_id(
        self,
        collaborator_id: UUID,
    ) -> ResourceCollaborator | None:
        """Find a collaborator row by its own primary key.

        Args:
            collaborator_id: The UUID of the collaborator record

        Returns:
            ResourceCollaborator if found, None otherwise
        """
        stmt = (
            select(ResourceCollaborator)
            .where(ResourceCollaborator.id == collaborator_id)
            .options(selectinload(ResourceCollaborator.user))
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def find_collaborator(
        self,
        resource_type: ResourceType,
        resource_id: UUID,
        user_id: UUID,
    ) -> ResourceCollaborator | None:
        """Find a collaborator row for a specific (resource_type, resource_id, user) triple.

        Args:
            resource_type: Type of resource
            resource_id: Resource UUID
            user_id: User UUID

        Returns:
            ResourceCollaborator if found, None otherwise
        """
        stmt = select(ResourceCollaborator).where(
            ResourceCollaborator.resource_type == resource_type,
            ResourceCollaborator.resource_id == resource_id,
            ResourceCollaborator.user_id == user_id,
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_role(
        self,
        resource_type: ResourceType,
        resource_id: UUID,
        user_id: UUID,
    ) -> CollaboratorRole | None:
        """Return the role for a user on a resource, or None if not a collaborator.

        Args:
            resource_type: Type of resource
            resource_id: Resource UUID
            user_id: User UUID

        Returns:
            CollaboratorRole if user is a collaborator, None otherwise
        """
        collab = await self.find_collaborator(resource_type, resource_id, user_id)
        return collab.role if collab else None

    async def check_permission(
        self,
        resource_type: ResourceType,
        resource_id: UUID,
        user_id: UUID,
        min_role: CollaboratorRole,
    ) -> bool:
        """Check if a user has at least the given minimum role on a resource.

        Args:
            resource_type: Type of resource
            resource_id: Resource UUID
            user_id: User UUID
            min_role: Minimum required role (uses CollaboratorRole ordering)

        Returns:
            True if user has sufficient permission, False otherwise
        """
        # Build the set of roles that satisfy min_role using the hierarchy
        if min_role == CollaboratorRole.OWNER:
            acceptable = [CollaboratorRole.OWNER]
        elif min_role == CollaboratorRole.EDITOR:
            acceptable = [CollaboratorRole.OWNER, CollaboratorRole.EDITOR]
        else:  # VIEWER — any role is acceptable
            acceptable = [
                CollaboratorRole.OWNER,
                CollaboratorRole.EDITOR,
                CollaboratorRole.VIEWER,
            ]

        stmt = (
            select(ResourceCollaborator.id)
            .where(
                ResourceCollaborator.resource_type == resource_type,
                ResourceCollaborator.resource_id == resource_id,
                ResourceCollaborator.user_id == user_id,
                ResourceCollaborator.role.in_(acceptable),
            )
            .limit(1)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def get_all_for_resource(
        self,
        resource_type: ResourceType,
        resource_id: UUID,
    ) -> list[ResourceCollaborator]:
        """Get all collaborator rows for a resource, with user eagerly loaded.

        Args:
            resource_type: Type of resource
            resource_id: Resource UUID

        Returns:
            List of ResourceCollaborator rows ordered by added_at
        """
        stmt = (
            select(ResourceCollaborator)
            .where(
                ResourceCollaborator.resource_type == resource_type,
                ResourceCollaborator.resource_id == resource_id,
            )
            .options(selectinload(ResourceCollaborator.user))
            .order_by(ResourceCollaborator.added_at)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def user_can_edit_question(
        self,
        question_id: UUID,
        user_id: UUID,
    ) -> bool:
        """Check if a user has owner or editor role on any assessment containing the question.

        Args:
            question_id: Question UUID
            user_id: User UUID

        Returns:
            True if the user can edit the question via assessment collaboration
        """
        stmt = (
            select(ResourceCollaborator.id)
            .join(
                AssessmentQuestion,
                AssessmentQuestion.assessment_id == ResourceCollaborator.resource_id,
            )
            .where(
                ResourceCollaborator.resource_type == ResourceType.ASSESSMENT,
                AssessmentQuestion.question_id == question_id,
                ResourceCollaborator.user_id == user_id,
                ResourceCollaborator.role.in_(
                    [CollaboratorRole.OWNER, CollaboratorRole.EDITOR]
                ),
            )
            .limit(1)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none() is not None
