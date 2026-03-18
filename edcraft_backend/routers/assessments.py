"""Assessment endpoints with question association management."""

from typing import Literal
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from edcraft_backend.dependencies import (
    AssessmentServiceDep,
    CurrentUserDep,
    CurrentUserOptionalDep,
)
from edcraft_backend.exceptions import EdCraftBaseException
from edcraft_backend.models.assessment import Assessment
from edcraft_backend.models.resource_collaborator import ResourceCollaborator
from edcraft_backend.schemas.assessment import (
    AddCollaboratorRequest,
    AssessmentResponse,
    AssessmentWithQuestionsResponse,
    CollaboratorResponse,
    CreateAssessmentRequest,
    InsertQuestionIntoAssessmentRequest,
    LinkQuestionToAssessmentRequest,
    ReorderQuestionsInAssessmentRequest,
    UpdateAssessmentRequest,
    UpdateCollaboratorRoleRequest,
)

router = APIRouter(prefix="/assessments", tags=["assessments"])


@router.post("", response_model=AssessmentResponse, status_code=status.HTTP_201_CREATED)
async def create_assessment(
    current_user: CurrentUserDep,
    assessment_data: CreateAssessmentRequest,
    service: AssessmentServiceDep,
) -> Assessment:
    """Create a new assessment."""
    try:
        return await service.create_assessment(current_user.id, assessment_data)
    except EdCraftBaseException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e


@router.get("", response_model=list[AssessmentResponse])
async def list_assessments(
    current_user: CurrentUserDep,
    service: AssessmentServiceDep,
    folder_id: UUID | None = Query(None, description="Filter by folder ID"),
    collab_filter: Literal["all", "owned", "shared"] = Query(
        "all", description="Filter by collaboration role: all, owned, or shared"
    ),
) -> list[AssessmentResponse]:
    """List assessments the user has access to, optionally filtered by folder or role."""
    try:
        return await service.list_assessments(
            user_id=current_user.id, folder_id=folder_id, collab_filter=collab_filter
        )
    except EdCraftBaseException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e


@router.get("/{assessment_id}", response_model=AssessmentWithQuestionsResponse)
async def get_assessment(
    current_user: CurrentUserOptionalDep,
    assessment_id: UUID,
    service: AssessmentServiceDep,
) -> AssessmentWithQuestionsResponse:
    """Get assessment with questions.

    - Collaborators can access the assessment
    - Unauthenticated users can only access public assessments
    - Returns 404 for private assessments accessed by non-collaborators
    """
    try:
        user_id = current_user.id if current_user else None
        return await service.get_assessment_with_questions(
            user_id=user_id, assessment_id=assessment_id
        )
    except EdCraftBaseException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e


@router.patch("/{assessment_id}", response_model=AssessmentResponse)
async def update_assessment(
    current_user: CurrentUserDep,
    assessment_id: UUID,
    assessment_data: UpdateAssessmentRequest,
    service: AssessmentServiceDep,
) -> Assessment:
    """Update assessment metadata. Requires edit permissions."""
    try:
        return await service.update_assessment(
            user_id=current_user.id,
            assessment_id=assessment_id,
            assessment_data=assessment_data,
        )
    except EdCraftBaseException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e


@router.delete("/{assessment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def soft_delete_assessment(
    current_user: CurrentUserDep,
    assessment_id: UUID,
    service: AssessmentServiceDep,
) -> None:
    """Soft delete an assessment. Owner only."""
    try:
        await service.soft_delete_assessment(
            user_id=current_user.id, assessment_id=assessment_id
        )
    except EdCraftBaseException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e


@router.post(
    "/{assessment_id}/questions",
    response_model=AssessmentWithQuestionsResponse,
    status_code=status.HTTP_201_CREATED,
)
async def insert_question_into_assessment(
    current_user: CurrentUserDep,
    assessment_id: UUID,
    question_data: InsertQuestionIntoAssessmentRequest,
    service: AssessmentServiceDep,
) -> AssessmentWithQuestionsResponse:
    """Add a question to an assessment. Requires edit permissions.

    Questions are ordered using 0-indexed consecutive integers (0, 1, 2, 3...).
    When adding a question with a specified order, questions at or after that
    position are automatically shifted down. Omit order to append to the end.

    Valid order range: 0 to current question count (inclusive).
    """
    try:
        return await service.add_question_to_assessment(
            current_user.id, assessment_id, question_data.question, question_data.order
        )
    except EdCraftBaseException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e


@router.post(
    "/{assessment_id}/questions/link",
    response_model=AssessmentWithQuestionsResponse,
    status_code=status.HTTP_201_CREATED,
)
async def link_question_into_assessment(
    current_user: CurrentUserDep,
    assessment_id: UUID,
    question_data: LinkQuestionToAssessmentRequest,
    service: AssessmentServiceDep,
) -> AssessmentWithQuestionsResponse:
    """Copy an existing question into an assessment and link to source question.
    Requires edit permissions for assessment and view permissions for question.

    Questions are ordered using 0-indexed consecutive integers (0, 1, 2, 3...).
    When linking a question with a specified order, questions at or after that
    position are automatically shifted down. Omit order to append to the end.

    Valid order range: 0 to current question count (inclusive).
    """
    try:
        return await service.link_question_to_assessment(
            current_user.id,
            assessment_id,
            question_data.question_id,
            question_data.order,
        )
    except EdCraftBaseException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e


@router.post(
    "/{assessment_id}/questions/{question_id}/sync",
    response_model=AssessmentWithQuestionsResponse,
)
async def sync_question_in_assessment(
    current_user: CurrentUserDep,
    assessment_id: UUID,
    question_id: UUID,
    service: AssessmentServiceDep,
) -> AssessmentWithQuestionsResponse:
    """Sync a linked question's content from its source. Requires edit permissions.

    Overwrites the question's content with the current content of its source question.
    Returns 400 if the question has no source link.
    """
    try:
        return await service.sync_question_in_assessment(
            current_user.id, assessment_id, question_id
        )
    except EdCraftBaseException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e


@router.post(
    "/{assessment_id}/questions/{question_id}/unlink",
    response_model=AssessmentWithQuestionsResponse,
    status_code=status.HTTP_200_OK,
)
async def unlink_question_in_assessment(
    current_user: CurrentUserDep,
    assessment_id: UUID,
    question_id: UUID,
    service: AssessmentServiceDep,
) -> AssessmentWithQuestionsResponse:
    """Sever the source link on a question without removing it. Requires edit permissions.
    The question content is preserved as a fully independent question.
    """
    try:
        return await service.unlink_question_in_assessment(
            current_user.id, assessment_id, question_id
        )
    except EdCraftBaseException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e


@router.delete(
    "/{assessment_id}/questions/{question_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def remove_question_from_assessment(
    current_user: CurrentUserDep,
    assessment_id: UUID,
    question_id: UUID,
    service: AssessmentServiceDep,
) -> None:
    """Remove a question from an assessment. Requires edit permissions."""
    try:
        await service.remove_question_from_assessment(
            current_user.id, assessment_id, question_id
        )
    except EdCraftBaseException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e


@router.patch(
    "/{assessment_id}/questions/reorder", response_model=AssessmentWithQuestionsResponse
)
async def reorder_questions(
    current_user: CurrentUserDep,
    assessment_id: UUID,
    reorder_data: ReorderQuestionsInAssessmentRequest,
    service: AssessmentServiceDep,
) -> AssessmentWithQuestionsResponse:
    """Reorder questions in an assessment. Requires edit permissions."""
    try:
        return await service.reorder_questions(
            current_user.id, assessment_id, reorder_data.question_orders
        )
    except EdCraftBaseException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e


@router.post(
    "/{assessment_id}/collaborators",
    response_model=CollaboratorResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_collaborator(
    current_user: CurrentUserDep,
    assessment_id: UUID,
    collaborator_data: AddCollaboratorRequest,
    service: AssessmentServiceDep,
) -> ResourceCollaborator:
    """Add a collaborator to an assessment. Editor or owner. Cannot assign owner role."""
    try:
        return await service.add_collaborator(
            caller_id=current_user.id,
            assessment_id=assessment_id,
            email=collaborator_data.email,
            role=collaborator_data.role,
        )
    except EdCraftBaseException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e


@router.get(
    "/{assessment_id}/collaborators",
    response_model=list[CollaboratorResponse],
)
async def list_collaborators(
    current_user: CurrentUserDep,
    assessment_id: UUID,
    service: AssessmentServiceDep,
) -> list[ResourceCollaborator]:
    """List collaborators for an assessment. Editor or owner only."""
    try:
        return await service.list_collaborators(
            caller_id=current_user.id, assessment_id=assessment_id
        )
    except EdCraftBaseException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e


@router.patch(
    "/{assessment_id}/collaborators/{collaborator_id}",
    response_model=CollaboratorResponse,
)
async def update_collaborator_role(
    current_user: CurrentUserDep,
    assessment_id: UUID,
    collaborator_id: UUID,
    role_data: UpdateCollaboratorRoleRequest,
    service: AssessmentServiceDep,
) -> ResourceCollaborator:
    """
    Update a collaborator's role. Editor or owner.
    Editors can assign editor/viewer. Owner can transfer ownership.
    """
    try:
        return await service.update_collaborator_role(
            caller_id=current_user.id,
            assessment_id=assessment_id,
            collaborator_id=collaborator_id,
            new_role=role_data.role,
        )
    except EdCraftBaseException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e


@router.delete(
    "/{assessment_id}/collaborators/{collaborator_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def remove_collaborator(
    current_user: CurrentUserDep,
    assessment_id: UUID,
    collaborator_id: UUID,
    service: AssessmentServiceDep,
) -> None:
    """Remove a collaborator from an assessment. Editor or owner. Cannot remove the owner."""
    try:
        await service.remove_collaborator(
            caller_id=current_user.id,
            assessment_id=assessment_id,
            collaborator_id=collaborator_id,
        )
    except EdCraftBaseException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
