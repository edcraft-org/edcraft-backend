"""Generic collaboration endpoints for all collaborable resources."""

from enum import Enum
from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from edcraft_backend.dependencies import (
    CollaborationServiceDep,
    CurrentUserDep,
)
from edcraft_backend.exceptions import EdCraftBaseException
from edcraft_backend.models.enums import ResourceType
from edcraft_backend.models.resource_collaborator import ResourceCollaborator
from edcraft_backend.schemas.collaboration import (
    AddCollaboratorRequest,
    CollaboratorResponse,
    UpdateCollaboratorRoleRequest,
)

router = APIRouter(tags=["collaborators"])


class ResourcePath(Enum):
    """URL path segments for collaborable resources, matching existing router prefixes."""

    ASSESSMENTS = "assessments"
    QUESTION_BANKS = "question-banks"
    QUESTION_TEMPLATE_BANKS = "question-template-banks"
    ASSESSMENT_TEMPLATES = "assessment-templates"


RESOURCE_PATH_TO_TYPE: dict[ResourcePath, ResourceType] = {
    ResourcePath.ASSESSMENTS: ResourceType.ASSESSMENT,
    ResourcePath.QUESTION_BANKS: ResourceType.QUESTION_BANK,
    ResourcePath.QUESTION_TEMPLATE_BANKS: ResourceType.QUESTION_TEMPLATE_BANK,
    ResourcePath.ASSESSMENT_TEMPLATES: ResourceType.ASSESSMENT_TEMPLATE,
}


@router.post(
    "/{resource_path}/{resource_id}/collaborators",
    response_model=CollaboratorResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_collaborator(
    resource_path: ResourcePath,
    resource_id: UUID,
    collaborator_data: AddCollaboratorRequest,
    current_user: CurrentUserDep,
    service: CollaborationServiceDep,
) -> ResourceCollaborator:
    """
    Add a collaborator to a resource.
    Cannot assign owner role.
    Requires editor or owner permissions.
    """
    try:
        resource_type = RESOURCE_PATH_TO_TYPE[resource_path]
        return await service.add_collaborator(
            caller_id=current_user.id,
            resource_type=resource_type,
            resource_id=resource_id,
            email=collaborator_data.email,
            role=collaborator_data.role,
        )
    except EdCraftBaseException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e


@router.get(
    "/{resource_path}/{resource_id}/collaborators",
    response_model=list[CollaboratorResponse],
)
async def list_collaborators(
    resource_path: ResourcePath,
    resource_id: UUID,
    current_user: CurrentUserDep,
    service: CollaborationServiceDep,
) -> list[ResourceCollaborator]:
    """List all collaborators for a resource. Requires editor or owner permissions."""
    try:
        resource_type = RESOURCE_PATH_TO_TYPE[resource_path]
        return await service.list_collaborators(
            caller_id=current_user.id,
            resource_type=resource_type,
            resource_id=resource_id,
        )
    except EdCraftBaseException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e


@router.patch(
    "/{resource_path}/{resource_id}/collaborators/{collaborator_id}",
    response_model=CollaboratorResponse,
)
async def update_collaborator_role(
    resource_path: ResourcePath,
    resource_id: UUID,
    collaborator_id: UUID,
    role_data: UpdateCollaboratorRoleRequest,
    current_user: CurrentUserDep,
    service: CollaborationServiceDep,
) -> ResourceCollaborator:
    """Update a collaborator's role. Requires editor or owner permissions.

    Editors can assign editor/viewer. Owner can transfer ownership.
    On ownership transfer: caller becomes editor, target becomes owner,
    resource moves to new owner's root folder.
    """
    try:
        resource_type = RESOURCE_PATH_TO_TYPE[resource_path]
        return await service.update_collaborator_role(
            caller_id=current_user.id,
            resource_type=resource_type,
            resource_id=resource_id,
            collaborator_id=collaborator_id,
            new_role=role_data.role,
        )
    except EdCraftBaseException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e


@router.delete(
    "/{resource_path}/{resource_id}/collaborators/{collaborator_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def remove_collaborator(
    resource_path: ResourcePath,
    resource_id: UUID,
    collaborator_id: UUID,
    current_user: CurrentUserDep,
    service: CollaborationServiceDep,
) -> None:
    """
    Remove a collaborator from a resource.
    Requires editor or owner permissions. Cannot remove the owner.
    """
    try:
        resource_type = RESOURCE_PATH_TO_TYPE[resource_path]
        await service.remove_collaborator(
            caller_id=current_user.id,
            resource_type=resource_type,
            resource_id=resource_id,
            collaborator_id=collaborator_id,
        )
    except EdCraftBaseException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
