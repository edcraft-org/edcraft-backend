"""Repository for ResourceCollaborator association operations."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from edcraft_backend.models.assessment import Assessment
from edcraft_backend.models.enums import (
    CollaboratorRole,
    ResourceType,
    ResourceVisibility,
)
from edcraft_backend.models.question import Question
from edcraft_backend.models.resource_collaborator import ResourceCollaborator
from edcraft_backend.repositories.base import AssociationRepository


class ResourceCollaboratorRepository(AssociationRepository[ResourceCollaborator]):
    """Repository for ResourceCollaborator association operations."""

    def __init__(self, db: AsyncSession):
        super().__init__(ResourceCollaborator, db)

    def _get_acceptable_roles(
        self, min_role: CollaboratorRole
    ) -> list[CollaboratorRole]:
        if min_role == CollaboratorRole.OWNER:
            return [CollaboratorRole.OWNER]
        elif min_role == CollaboratorRole.EDITOR:
            return [CollaboratorRole.OWNER, CollaboratorRole.EDITOR]
        else:  # VIEWER
            return [
                CollaboratorRole.OWNER,
                CollaboratorRole.EDITOR,
                CollaboratorRole.VIEWER,
            ]

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
        return CollaboratorRole(collab.role) if collab else None

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
        acceptable = self._get_acceptable_roles(min_role)

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

    async def check_question_permission(
        self,
        question_id: UUID,
        user_id: UUID,
        min_role: CollaboratorRole,
    ) -> bool:
        """Check if a user has sufficient access to a question.

        Access is granted if the user:
        - owns the question, OR
        - has at least min_role on any assessment containing the question, OR
        - (min_role=VIEWER only) the question is in a public assessment.

        Args:
            question_id: Question UUID
            user_id: User UUID
            min_role: Minimum required role (VIEWER or EDITOR)

        Returns:
            True if the user has sufficient permission
        """
        acceptable_roles = self._get_acceptable_roles(min_role)

        # Check ownership
        owner_stmt = (
            select(Question.id)
            .where(Question.id == question_id, Question.owner_id == user_id)
            .limit(1)
        )
        result = await self.db.execute(owner_stmt)
        if result.scalar_one_or_none() is not None:
            return True

        # Build conditions for assessment-based access
        collab_condition = (
            select(ResourceCollaborator.id)
            .join(
                Question,
                Question.assessment_id == ResourceCollaborator.resource_id,
            )
            .where(
                ResourceCollaborator.resource_type == ResourceType.ASSESSMENT,
                Question.id == question_id,
                ResourceCollaborator.user_id == user_id,
                ResourceCollaborator.role.in_(acceptable_roles),
            )
            .limit(1)
        )
        result = await self.db.execute(collab_condition)
        if result.scalar_one_or_none() is not None:
            return True

        # For VIEWER, also allow access if question is in any public assessment
        if min_role == CollaboratorRole.VIEWER:
            public_stmt = (
                select(Question.id)
                .join(
                    Assessment,
                    Assessment.id == Question.assessment_id,
                )
                .where(
                    Question.id == question_id,
                    Assessment.visibility == ResourceVisibility.PUBLIC,
                    Assessment.deleted_at.is_(None),
                )
                .limit(1)
            )
            result = await self.db.execute(public_stmt)
            if result.scalar_one_or_none() is not None:
                return True

        return False
