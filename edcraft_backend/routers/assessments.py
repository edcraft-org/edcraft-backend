"""Assessment endpoints with question association management."""

from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from edcraft_backend.dependencies import AssessmentServiceDep, CurrentUserDep
from edcraft_backend.exceptions import EdCraftBaseException
from edcraft_backend.models.assessment import Assessment
from edcraft_backend.schemas.assessment import (
    AssessmentResponse,
    AssessmentWithQuestionsResponse,
    CreateAssessmentRequest,
    InsertQuestionIntoAssessmentRequest,
    LinkQuestionToAssessmentRequest,
    ReorderQuestionsInAssessmentRequest,
    UpdateAssessmentRequest,
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
) -> list[Assessment]:
    """List assessments by owner, optionally filtered by folder."""
    try:
        return await service.list_assessments(
            user_id=current_user.id, folder_id=folder_id
        )
    except EdCraftBaseException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e


@router.get("/{assessment_id}", response_model=AssessmentWithQuestionsResponse)
async def get_assessment(
    current_user: CurrentUserDep,
    assessment_id: UUID,
    service: AssessmentServiceDep,
) -> AssessmentWithQuestionsResponse:
    """Get assessment with questions in order."""
    try:
        return await service.get_assessment_with_questions(
            user_id=current_user.id, assessment_id=assessment_id
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
    """Update assessment metadata."""
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
    """Soft delete an assessment and clean up orphaned questions."""
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
    """Add a question to an assessment.

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
    """Link an existing question into an assessment.

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


@router.delete(
    "/{assessment_id}/questions/{question_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def remove_question_from_assessment(
    current_user: CurrentUserDep,
    assessment_id: UUID,
    question_id: UUID,
    service: AssessmentServiceDep,
) -> None:
    """Remove a question from an assessment and clean up if orphaned."""
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
    """Reorder questions in an assessment."""
    try:
        return await service.reorder_questions(
            current_user.id, assessment_id, reorder_data.question_orders
        )
    except EdCraftBaseException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
