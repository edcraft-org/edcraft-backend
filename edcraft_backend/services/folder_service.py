from uuid import UUID

from edcraft_backend.exceptions import (
    CircularReferenceError,
    DuplicateResourceError,
    ForbiddenOperationError,
    ResourceNotFoundError,
)
from edcraft_backend.models.folder import Folder
from edcraft_backend.repositories.assessment_repository import AssessmentRepository
from edcraft_backend.repositories.assessment_template_repository import (
    AssessmentTemplateRepository,
)
from edcraft_backend.repositories.folder_repository import FolderRepository
from edcraft_backend.schemas.folder import (
    CreateFolderRequest,
    FolderResponse,
    FolderTreeResponse,
    FolderWithContentsResponse,
    MoveFolderRequest,
    UpdateFolderRequest,
)
from edcraft_backend.services.question_service import QuestionService
from edcraft_backend.services.question_template_service import QuestionTemplateService


class FolderService:
    """Service layer for Folder business logic."""

    def __init__(
        self,
        folder_repository: FolderRepository,
        assessment_repository: AssessmentRepository,
        assessment_template_repository: AssessmentTemplateRepository,
        question_service: QuestionService,
        question_template_service: QuestionTemplateService,
    ):
        self.folder_repo = folder_repository
        self.assessment_repo = assessment_repository
        self.assessment_template_repo = assessment_template_repository
        self.question_svc = question_service
        self.question_template_svc = question_template_service

    async def create_root_folder(self, owner_id: UUID) -> Folder:
        """Create root folder for a new user.

        Args:
            owner_id: User UUID

        Returns:
            Created root folder
        """
        root_folder = Folder(
            owner_id=owner_id,
            parent_id=None,
            name="My Projects",
        )
        return await self.folder_repo.create(root_folder)

    async def create_folder(self, folder_data: CreateFolderRequest) -> Folder:
        """Create a new folder.

        Args:
            folder_data: Folder creation data

        Returns:
            Created folder

        Raises:
            DuplicateResourceError: If folder name already exists in parent
            ResourceNotFoundError: If parent folder does not exist
        """
        # Verify parent exists
        parent = await self.folder_repo.get_by_id(folder_data.parent_id)
        if not parent:
            raise ResourceNotFoundError("Folder", str(folder_data.parent_id))

        # Check for duplicate name in same parent
        if await self.folder_repo.folder_name_exists(
            folder_data.owner_id,
            folder_data.name,
            folder_data.parent_id,
        ):
            raise DuplicateResourceError(
                "Folder",
                "name",
                f"{folder_data.name} in this location",
            )

        folder = Folder(**folder_data.model_dump())
        return await self.folder_repo.create(folder)

    async def list_folders(
        self,
        owner_id: UUID,
        parent_id: UUID | None = None,
    ) -> list[Folder]:
        """List folders for a user, filtered by parent.

        Args:
            owner_id: User UUID
            parent_id: Parent folder UUID (None for ALL folders owned by user)

        Returns:
            List of folders ordered by name
        """
        if parent_id is None:
            return await self.folder_repo.list(
                filters={"owner_id": owner_id},
                order_by=Folder.name.asc()
            )
        else:
            return await self.folder_repo.get_children(parent_id)

    async def get_root_folder(self, owner_id: UUID) -> Folder:
        """Get the root folder for a user.

        Args:
            owner_id: User UUID

        Returns:
            Root folder
        """
        return await self.folder_repo.get_root_folder(owner_id)

    async def get_folder(self, folder_id: UUID) -> Folder:
        """Get a folder by ID.

        Args:
            folder_id: Folder UUID

        Returns:
            Folder entity

        Raises:
            ResourceNotFoundError: If folder not found
        """
        folder = await self.folder_repo.get_by_id(folder_id)
        if not folder:
            raise ResourceNotFoundError("Folder", str(folder_id))
        return folder

    async def get_folder_with_contents(self, folder_id: UUID) -> FolderWithContentsResponse:
        """Get a folder with its complete contents (assessments, templates, and child folders).

        Args:
            folder_id: Folder UUID

        Returns:
            Folder with complete Assessment, AssessmentTemplate, and child Folder objects

        Raises:
            ResourceNotFoundError: If folder not found
        """
        from edcraft_backend.schemas.assessment import AssessmentResponse
        from edcraft_backend.schemas.assessment_template import AssessmentTemplateResponse

        folder = await self.get_folder(folder_id)

        assessment_responses = [
            AssessmentResponse.model_validate(assessment)
            for assessment in folder.assessments
            if assessment.deleted_at is None
        ]

        template_responses = [
            AssessmentTemplateResponse.model_validate(template)
            for template in folder.assessment_templates
            if template.deleted_at is None
        ]

        children = await self.folder_repo.get_children(folder_id)
        folder_responses = [FolderResponse.model_validate(child) for child in children]

        return FolderWithContentsResponse(
            id=folder.id,
            owner_id=folder.owner_id,
            parent_id=folder.parent_id,
            name=folder.name,
            description=folder.description,
            created_at=folder.created_at,
            updated_at=folder.updated_at,
            assessments=assessment_responses,
            assessment_templates=template_responses,
            folders=folder_responses,
        )

    async def get_folder_tree(self, folder_id: UUID) -> FolderTreeResponse:
        """Get folder with full subtree.

        Args:
            folder_id: Folder UUID

        Returns:
            Folder tree structure

        Raises:
            ResourceNotFoundError: If folder not found
        """
        folder = await self.folder_repo.get_by_id(folder_id)
        if not folder:
            raise ResourceNotFoundError("Folder", str(folder_id))

        return await self._build_folder_tree(folder)

    async def _build_folder_tree(self, folder: Folder) -> FolderTreeResponse:
        """Recursively build folder tree structure."""
        children = await self.folder_repo.get_children(folder.id)

        children_trees: list[FolderTreeResponse] = []
        for child in children:
            child_tree = await self._build_folder_tree(child)
            children_trees.append(child_tree)

        return FolderTreeResponse(
            id=folder.id,
            owner_id=folder.owner_id,
            parent_id=folder.parent_id,
            name=folder.name,
            description=folder.description,
            created_at=folder.created_at,
            children=children_trees,
        )

    async def get_folder_path(self, folder_id: UUID) -> list[Folder]:
        """Get the path from root to the given folder.

        Args:
            folder_id: Folder UUID

        Returns:
            List of folders from root to current

        Raises:
            ResourceNotFoundError: If folder not found
        """
        path: list[Folder] = []
        current_id: UUID | None = folder_id

        while current_id is not None:
            folder = await self.folder_repo.get_by_id(current_id)
            if not folder:
                break

            path.insert(0, folder)
            current_id = folder.parent_id

        if not path:
            raise ResourceNotFoundError("Folder", str(folder_id))

        return path

    async def update_folder(self, folder_id: UUID, folder_data: UpdateFolderRequest) -> Folder:
        """Update folder name or description.

        Args:
            folder_id: Folder UUID
            folder_data: Folder update data

        Returns:
            Updated folder

        Raises:
            ResourceNotFoundError: If folder not found
            DuplicateResourceError: If name already exists in parent
        """
        folder = await self.get_folder(folder_id)
        update_data = folder_data.model_dump(exclude_unset=True)

        # Check for name conflict if name is being updated
        if "name" in update_data and update_data["name"] != folder.name:
            if await self.folder_repo.folder_name_exists(
                folder.owner_id,
                update_data["name"],
                folder.parent_id,
                exclude_id=folder_id,
            ):
                raise DuplicateResourceError(
                    "Folder",
                    "name",
                    f"{update_data['name']} in this location",
                )

        # Apply updates
        for key, value in update_data.items():
            setattr(folder, key, value)

        return await self.folder_repo.update(folder)

    async def move_folder(self, folder_id: UUID, move_data: MoveFolderRequest) -> Folder:
        """Move folder to a different parent.

        Args:
            folder_id: Folder UUID
            move_data: Move operation data

        Returns:
            Updated folder

        Raises:
            ResourceNotFoundError: If folder or target parent not found
            CircularReferenceError: If move would create circular reference
            DuplicateResourceError: If name already exists in target location
        """
        folder = await self.get_folder(folder_id)

        # Check for circular reference
        if await self._check_circular_reference(folder_id, move_data.parent_id):
            raise CircularReferenceError()

        # Verify new parent exists
        parent = await self.folder_repo.get_by_id(move_data.parent_id)
        if not parent:
            raise ResourceNotFoundError("Folder", str(move_data.parent_id))

        # Check for name conflict in target location
        if await self.folder_repo.folder_name_exists(
            folder.owner_id,
            folder.name,
            move_data.parent_id,
            exclude_id=folder_id,
        ):
            raise DuplicateResourceError(
                "Folder",
                "name",
                f"{folder.name} in the target location",
            )

        folder.parent_id = move_data.parent_id
        return await self.folder_repo.update(folder)

    async def _check_circular_reference(
        self,
        folder_id: UUID,
        new_parent_id: UUID,
    ) -> bool:
        """Check if moving a folder would create a circular reference."""
        # Can't move a folder into itself
        if folder_id == new_parent_id:
            return True
        return await self.folder_repo.is_ancestor(folder_id, new_parent_id)

    async def soft_delete_folder(
        self, folder_id: UUID
    ) -> Folder:
        """Soft delete folder and all descendants using bulk operations.

        Args:
            folder_id: Folder UUID

        Returns:
            Soft-deleted folder

        Raises:
            ResourceNotFoundError: If folder not found
            ForbiddenOperationError: If attempting to delete root folder
        """
        folder = await self.folder_repo.get_by_id(folder_id)
        if not folder:
            raise ResourceNotFoundError("Folder", str(folder_id))
        if folder.parent_id is None:
            raise ForbiddenOperationError("Cannot delete root folder")

        descendant_ids = await self.folder_repo.get_all_descendant_ids(folder_id)
        all_folder_ids = [folder_id] + descendant_ids

        await self.folder_repo.bulk_soft_delete_by_ids(all_folder_ids)
        await self.assessment_repo.bulk_soft_delete_by_folder_ids(all_folder_ids)
        await self.assessment_template_repo.bulk_soft_delete_by_folder_ids(
            all_folder_ids
        )
        await self.question_svc.cleanup_orphaned_questions(folder.owner_id)
        await self.question_template_svc.cleanup_orphaned_templates(folder.owner_id)

        folder = await self.folder_repo.get_by_id(folder_id, include_deleted=True)
        if not folder:
            raise ResourceNotFoundError("Folder", str(folder_id))

        return folder
