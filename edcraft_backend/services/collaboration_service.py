"""Generic collaboration service for all collaborable resources."""

from uuid import UUID

from edcraft_backend.exceptions import (
    DuplicateResourceError,
    ResourceNotFoundError,
    UnauthorizedAccessError,
    ValidationError,
)
from edcraft_backend.models.assessment import Assessment
from edcraft_backend.models.assessment_template import AssessmentTemplate
from edcraft_backend.models.enums import (
    CollaboratorRole,
    ResourceType,
    ResourceVisibility,
)
from edcraft_backend.models.question_bank import QuestionBank
from edcraft_backend.models.question_template_bank import QuestionTemplateBank
from edcraft_backend.models.resource_collaborator import ResourceCollaborator
from edcraft_backend.repositories.assessment_repository import AssessmentRepository
from edcraft_backend.repositories.assessment_template_repository import (
    AssessmentTemplateRepository,
)
from edcraft_backend.repositories.question_bank_repository import QuestionBankRepository
from edcraft_backend.repositories.question_template_bank_repository import (
    QuestionTemplateBankRepository,
)
from edcraft_backend.repositories.resource_collaborator_repository import (
    ResourceCollaboratorRepository,
)
from edcraft_backend.repositories.user_repository import UserRepository
from edcraft_backend.services.folder_service import FolderService


class CollaborationService:
    """Generic service for collaborator management across all resource types."""

    def __init__(
        self,
        collaborator_repo: ResourceCollaboratorRepository,
        user_repo: UserRepository,
        folder_svc: FolderService,
        assessment_repo: AssessmentRepository,
        question_bank_repo: QuestionBankRepository,
        qt_bank_repo: QuestionTemplateBankRepository,
        assessment_template_repo: AssessmentTemplateRepository,
    ):
        self.collaborator_repo = collaborator_repo
        self.user_repo = user_repo
        self.folder_svc = folder_svc
        self.assessment_repo = assessment_repo
        self.question_bank_repo = question_bank_repo
        self.qt_bank_repo = qt_bank_repo
        self.assessment_template_repo = assessment_template_repo

    async def _get_resource(
        self,
        resource_type: ResourceType,
        resource_id: UUID,
    ) -> Assessment | QuestionBank | QuestionTemplateBank | AssessmentTemplate:
        """Fetch the resource from the right repository.

        Raises:
            ResourceNotFoundError: If the resource does not exist
        """
        resource: (
            Assessment | QuestionBank | QuestionTemplateBank | AssessmentTemplate | None
        ) = None
        if resource_type == ResourceType.ASSESSMENT:
            resource = await self.assessment_repo.get_by_id(resource_id)
        elif resource_type == ResourceType.QUESTION_BANK:
            resource = await self.question_bank_repo.get_by_id(resource_id)
        elif resource_type == ResourceType.QUESTION_TEMPLATE_BANK:
            resource = await self.qt_bank_repo.get_by_id(resource_id)
        elif resource_type == ResourceType.ASSESSMENT_TEMPLATE:
            resource = await self.assessment_template_repo.get_by_id(resource_id)

        if not resource:
            raise ResourceNotFoundError(resource_type.resource_name, str(resource_id))
        return resource

    async def check_access(
        self,
        resource_type: ResourceType,
        resource_id: UUID,
        user_id: UUID | None,
        min_role: CollaboratorRole,
    ) -> None:
        """Check if the user has at least the required role for the resource.

        Args:
            resource_type: Type of the resource
            resource_id: ID of the resource
            user_id: User UUID (can be None for unauthenticated access)
            min_role: Minimum required role (VIEWER, EDITOR, OWNER)

        Raises:
            UnauthorizedAccessError: If user lacks sufficient access
        """
        has_perm = False
        if user_id:
            has_perm = await self.collaborator_repo.check_permission(
                resource_type, resource_id, user_id, min_role
            )

        if not has_perm and min_role == CollaboratorRole.VIEWER:
            resource = await self._get_resource(resource_type, resource_id)
            has_perm = (
                hasattr(resource, "visibility")
                and resource.visibility == ResourceVisibility.PUBLIC
            )

        if not has_perm:
            raise UnauthorizedAccessError(resource_type.resource_name, str(resource_id))

    async def add_collaborator(
        self,
        caller_id: UUID,
        resource_type: ResourceType,
        resource_id: UUID,
        email: str,
        role: CollaboratorRole,
    ) -> ResourceCollaborator:
        """Add a collaborator to a resource. Caller must have EDITOR or OWNER role.

        Args:
            caller_id: User UUID of the caller (must be editor or owner)
            resource_type: Type of the resource
            resource_id: ID of the resource
            email: Email address of the user to add
            role: Role to assign (must not be OWNER)

        Returns:
            Created ResourceCollaborator

        Raises:
            UnauthorizedAccessError: If caller lacks EDITOR+ role
            ValidationError: If role is OWNER
            ResourceNotFoundError: If resource or target user not found
            DuplicateResourceError: If user is already a collaborator
        """
        await self._get_resource(resource_type, resource_id)
        await self.check_access(
            resource_type, resource_id, caller_id, CollaboratorRole.EDITOR
        )

        if role == CollaboratorRole.OWNER:
            raise ValidationError(
                "Cannot assign 'owner' role via collaborator management."
            )

        target_user = await self.user_repo.get_by_email(email)
        if not target_user:
            raise ResourceNotFoundError("User", f"email={email}")

        existing = await self.collaborator_repo.find_collaborator(
            resource_type, resource_id, target_user.id
        )
        if existing:
            raise DuplicateResourceError(
                "ResourceCollaborator",
                "resource_id/user_id",
                f"{resource_type.resource_name}={resource_id}, user={target_user.id}",
            )

        collab = ResourceCollaborator(
            resource_type=resource_type,
            resource_id=resource_id,
            user_id=target_user.id,
            role=role,
        )
        created = await self.collaborator_repo.create(collab)

        loaded = await self.collaborator_repo.find_by_id(created.id)
        if not loaded:
            raise ResourceNotFoundError("ResourceCollaborator", f"id={created.id}")
        return loaded

    async def list_collaborators(
        self,
        caller_id: UUID,
        resource_type: ResourceType,
        resource_id: UUID,
    ) -> list[ResourceCollaborator]:
        """List all collaborators for a resource. Caller must have EDITOR or OWNER role.

        Returns:
            List of ResourceCollaborator rows (with user eagerly loaded)

        Raises:
            UnauthorizedAccessError: If caller lacks EDITOR+ role
            ResourceNotFoundError: If resource not found
        """
        await self._get_resource(resource_type, resource_id)
        await self.check_access(
            resource_type, resource_id, caller_id, CollaboratorRole.EDITOR
        )
        return await self.collaborator_repo.get_all_for_resource(
            resource_type, resource_id
        )

    async def update_collaborator_role(
        self,
        caller_id: UUID,
        resource_type: ResourceType,
        resource_id: UUID,
        collaborator_id: UUID,
        new_role: CollaboratorRole,
    ) -> ResourceCollaborator:
        """Update a collaborator's role. Caller must have EDITOR or OWNER role.

        - Editors can assign editor or viewer but not owner.
        - Ownership transfer (new_role=OWNER): owner-only; caller becomes editor,
          resource moves to new owner's root folder.

        Args:
            caller_id: User UUID of the caller (must be editor or owner)
            resource_type: Type of the resource
            resource_id: ID of the resource
            collaborator_id: UUID of the collaborator record to update
            new_role: New role to assign

        Returns:
            Updated ResourceCollaborator

        Raises:
            UnauthorizedAccessError: If caller lacks EDITOR+ role
            ValidationError: If role constraints are violated
            ResourceNotFoundError: If resource or collaborator not found
        """
        resource = await self._get_resource(resource_type, resource_id)
        await self.check_access(
            resource_type, resource_id, caller_id, CollaboratorRole.EDITOR
        )

        caller_role_raw = await self.collaborator_repo.get_role(
            resource_type, resource_id, caller_id
        )
        caller_role = CollaboratorRole(caller_role_raw) if caller_role_raw else None

        collab = await self.collaborator_repo.find_by_id(collaborator_id)
        if not collab or collab.resource_id != resource_id:
            raise ResourceNotFoundError(
                "ResourceCollaborator",
                f"id={collaborator_id}",
            )

        if new_role == CollaboratorRole.OWNER:
            if caller_role != CollaboratorRole.OWNER:
                raise ValidationError("Only the owner can transfer ownership.")
            if collab.role == CollaboratorRole.OWNER:
                raise ValidationError("Target user is already the owner.")
            # Demote caller to editor, promote target to owner
            caller_collab = await self.collaborator_repo.find_collaborator(
                resource_type, resource_id, caller_id
            )
            if caller_collab:
                caller_collab.role = CollaboratorRole.EDITOR
            collab.role = CollaboratorRole.OWNER
            # Move resource to new owner's root folder
            new_owner_root = await self.folder_svc.get_root_folder(collab.user_id)
            if new_owner_root:
                resource.folder_id = new_owner_root.id
            resource.owner_id = collab.user_id
            await self.collaborator_repo.db.flush()
            await self.collaborator_repo.db.refresh(collab)
            return collab

        if collab.role == CollaboratorRole.OWNER:
            raise ValidationError(
                "Cannot change the owner's role directly. Use ownership transfer instead."
            )

        if (
            caller_role == CollaboratorRole.EDITOR
            and new_role == CollaboratorRole.OWNER
        ):
            raise ValidationError("Editors cannot assign the 'owner' role.")

        collab.role = new_role
        await self.collaborator_repo.db.flush()
        await self.collaborator_repo.db.refresh(collab)
        return collab

    async def remove_collaborator(
        self,
        caller_id: UUID,
        resource_type: ResourceType,
        resource_id: UUID,
        collaborator_id: UUID,
    ) -> None:
        """Remove a collaborator. Caller must have EDITOR or OWNER role.

        Cannot remove the owner row.

        Args:
            caller_id: User UUID of the caller (must be editor or owner)
            assessment_id: Assessment UUID
            collaborator_id: UUID of the collaborator record to remove

        Raises:
            UnauthorizedAccessError: If caller lacks EDITOR+ role
            ValidationError: If trying to remove the owner
            ResourceNotFoundError: If resource or collaborator not found
        """
        await self._get_resource(resource_type, resource_id)
        await self.check_access(
            resource_type, resource_id, caller_id, CollaboratorRole.EDITOR
        )

        collab = await self.collaborator_repo.find_by_id(collaborator_id)
        if not collab or collab.resource_id != resource_id:
            raise ResourceNotFoundError(
                "ResourceCollaborator",
                f"id={collaborator_id}",
            )

        if collab.role == CollaboratorRole.OWNER:
            raise ValidationError("Cannot remove the owner.")

        await self.collaborator_repo.hard_delete(collab)
