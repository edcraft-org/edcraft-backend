from uuid import UUID

from edcraft_backend.exceptions import (
    DataIntegrityError,
    DuplicateResourceError,
    ResourceNotFoundError,
    UnauthorizedAccessError,
    ValidationError,
)
from edcraft_backend.models.assessment import Assessment
from edcraft_backend.models.assessment_question import AssessmentQuestion
from edcraft_backend.models.enums import AssessmentVisibility
from edcraft_backend.repositories.assessment_question_repository import (
    AssessmentQuestionRepository,
)
from edcraft_backend.repositories.assessment_repository import AssessmentRepository
from edcraft_backend.schemas.assessment import (
    AssessmentMCQResponse,
    AssessmentMRQResponse,
    AssessmentQuestionResponse,
    AssessmentShortAnswerResponse,
    AssessmentWithQuestionsResponse,
    CreateAssessmentRequest,
    QuestionOrder,
    UpdateAssessmentRequest,
)
from edcraft_backend.schemas.question import CreateQuestionRequest
from edcraft_backend.services.folder_service import FolderService
from edcraft_backend.services.question_service import QuestionService


class AssessmentService:
    """Service layer for Assessment business logic."""

    def __init__(
        self,
        assessment_repository: AssessmentRepository,
        folder_svc: FolderService,
        assessment_question_repository: AssessmentQuestionRepository,
        question_service: QuestionService,
    ):
        self.assessment_repo = assessment_repository
        self.folder_svc = folder_svc
        self.assoc_repo = assessment_question_repository
        self.question_svc = question_service

    async def get_owned_assessment(
        self, user_id: UUID, assessment_id: UUID
    ) -> Assessment:
        """Get assessment and verify ownership.

        Args:
            user_id: User UUID
            assessment_id: Assessment UUID

        Returns:
            Assessment entity

        Raises:
            ResourceNotFoundError: If assessment not found
            UnauthorizedAccessError: If user doesn't own the assessment
        """
        assessment = await self.assessment_repo.get_by_id(assessment_id)
        if not assessment:
            raise ResourceNotFoundError("Assessment", str(assessment_id))
        if assessment.owner_id != user_id:
            raise UnauthorizedAccessError("Assessment", str(assessment_id))
        return assessment

    async def create_assessment(
        self, user_id: UUID, assessment_data: CreateAssessmentRequest
    ) -> Assessment:
        """Create a new assessment.

        Args:
            user_id: User UUID
            assessment_data: Assessment creation data

        Returns:
            Created assessment

        Raises:
            ResourceNotFoundError: If folder not found
            UnauthorizedAccessError: If user doesn't own the folder
        """
        await self.folder_svc.get_owned_folder(user_id, assessment_data.folder_id)

        assessment = Assessment(owner_id=user_id, **assessment_data.model_dump())
        return await self.assessment_repo.create(assessment)

    async def list_assessments(
        self,
        user_id: UUID,
        folder_id: UUID | None = None,
    ) -> list[Assessment]:
        """List assessments within folder or all user assessments.

        Args:
            user_id: User UUID
            folder_id: Folder UUID (None for ALL assessments owned by user)

        Returns:
            List of assessments ordered by updated_at descending

        Raises:
            ResourceNotFoundError: If folder not found
            UnauthorizedAccessError: If folder does not belong to user
        """
        if folder_id:
            await self.folder_svc.get_owned_folder(user_id, folder_id)
            assessments = await self.assessment_repo.get_by_folder(folder_id)
        else:
            assessments = await self.assessment_repo.list(
                filters={"owner_id": user_id},
                order_by=Assessment.updated_at.desc(),
            )

        return assessments

    async def get_assessment(self, user_id: UUID, assessment_id: UUID) -> Assessment:
        """Get an assessment by ID and verify ownership.

        Args:
            user_id: User UUID
            assessment_id: Assessment UUID

        Returns:
            Assessment entity

        Raises:
            ResourceNotFoundError: If assessment not found
            UnauthorizedAccessError: If user doesn't own the assessment
        """
        return await self.get_owned_assessment(user_id, assessment_id)

    async def update_assessment(
        self,
        user_id: UUID,
        assessment_id: UUID,
        assessment_data: UpdateAssessmentRequest,
    ) -> Assessment:
        """Update an assessment.

        Args:
            user_id: User UUID
            assessment_id: Assessment UUID
            assessment_data: Assessment update data

        Returns:
            Updated assessment

        Raises:
            ResourceNotFoundError: If assessment or folder not found
            UnauthorizedAccessError: If user doesn't own resources
        """
        assessment = await self.get_owned_assessment(user_id, assessment_id)
        update_data = assessment_data.model_dump(exclude_unset=True)

        if "folder_id" in update_data and update_data["folder_id"]:
            await self.folder_svc.get_owned_folder(user_id, update_data["folder_id"])

        for key, value in update_data.items():
            setattr(assessment, key, value)

        return await self.assessment_repo.update(assessment)

    async def soft_delete_assessment(
        self, user_id: UUID, assessment_id: UUID
    ) -> Assessment:
        """Soft delete an assessment and clean up orphaned questions.

        Args:
            user_id: User UUID
            assessment_id: Assessment UUID

        Returns:
            Soft-deleted assessment

        Raises:
            ResourceNotFoundError: If assessment not found
            UnauthorizedAccessError: If user doesn't own the assessment
        """
        assessment = await self.get_owned_assessment(user_id, assessment_id)
        deleted_assessment = await self.assessment_repo.soft_delete(assessment)
        await self.question_svc.cleanup_orphaned_questions(assessment.owner_id)
        return deleted_assessment

    def _build_assessment_question_response(
        self, assoc: AssessmentQuestion
    ) -> AssessmentQuestionResponse:
        """Build the appropriate response type for an assessment question.

        Args:
            assoc: AssessmentQuestion association

        Returns:
            AssessmentQuestionResponse subtype based on question_type

        Raises:
            DataIntegrityError: If question type is unknown
        """
        q = assoc.question

        base_data = {
            "id": q.id,
            "owner_id": q.owner_id,
            "template_id": q.template_id,
            "question_type": q.question_type,
            "question_text": q.question_text,
            "created_at": q.created_at,
            "updated_at": q.updated_at,
            "order": assoc.order,
            "added_at": assoc.added_at,
        }

        if q.question_type == "mcq":
            return AssessmentMCQResponse.model_validate(
                {**base_data, "mcq_data": q.data}
            )
        elif q.question_type == "mrq":
            return AssessmentMRQResponse.model_validate(
                {**base_data, "mrq_data": q.data}
            )
        elif q.question_type == "short_answer":
            return AssessmentShortAnswerResponse.model_validate(
                {**base_data, "short_answer_data": q.data}
            )
        else:
            raise DataIntegrityError(f"Unknown question type: {q.question_type}")

    async def get_assessment_with_questions(
        self, user_id: UUID | None, assessment_id: UUID
    ) -> AssessmentWithQuestionsResponse:
        """Get assessment with all questions loaded.

        Args:
            user_id: User UUID (None for unauthenticated users)
            assessment_id: Assessment UUID

        Returns:
            Assessment with questions

        Raises:
            ResourceNotFoundError: If assessment not found or access denied
        """
        assessment = await self.assessment_repo.get_by_id_with_questions(assessment_id)
        if not assessment:
            raise ResourceNotFoundError("Assessment", str(assessment_id))

        is_owner = user_id and assessment.owner_id == user_id
        is_public = assessment.visibility == AssessmentVisibility.PUBLIC

        if not (is_owner or is_public):
            raise ResourceNotFoundError("Assessment", str(assessment_id))

        # Filter out soft-deleted questions
        questions: list[AssessmentQuestionResponse] = []
        for assoc in assessment.question_associations:
            if assoc.question and assoc.question.deleted_at is None:
                question_response = self._build_assessment_question_response(assoc)
                questions.append(question_response)

        return AssessmentWithQuestionsResponse(
            id=assessment.id,
            owner_id=assessment.owner_id,
            folder_id=assessment.folder_id,
            title=assessment.title,
            description=assessment.description,
            visibility=assessment.visibility,
            created_at=assessment.created_at,
            updated_at=assessment.updated_at,
            questions=questions,
        )

    async def add_question_to_assessment(
        self,
        user_id: UUID,
        assessment_id: UUID,
        question: CreateQuestionRequest,
        order: int | None = None,
    ) -> AssessmentWithQuestionsResponse:
        """Add a question to an assessment.

        Args:
            user_id: User UUID
            assessment_id: Assessment UUID
            question: QuestionCreate object
            order: Order position for the question

        Returns:
            Updated assessment with questions

        Raises:
            ResourceNotFoundError: If assessment or question not found
            ValidationError: If order is invalid
            UnauthorizedAccessError: If user doesn't own the assessment
        """
        # Verify assessment exists and ownership
        assessment = await self.get_owned_assessment(user_id, assessment_id)

        # Create question
        question_entity = await self.question_svc.create_question(user_id, question)

        # Validate and determine order
        current_count = await self.assoc_repo.get_count(assessment_id)

        if order is not None and (order < 0 or order > current_count):
            raise ValidationError(
                f"Order must be between 0 and {current_count}. "
                "Omit order to append to the end."
            )

        if order is None:
            order = current_count

        if order < current_count:
            await self.assoc_repo.shift_orders_from(assessment_id, order)

        # Create association
        assoc = AssessmentQuestion(
            assessment_id=assessment_id,
            question_id=question_entity.id,
            order=order,
        )
        await self.assoc_repo.create(assoc)

        # Expire the cached assessment to force fresh query
        self.assessment_repo.db.expire(assessment)

        # Return updated assessment with questions
        return await self.get_assessment_with_questions(user_id, assessment_id)

    async def link_question_to_assessment(
        self,
        user_id: UUID,
        assessment_id: UUID,
        question_id: UUID,
        order: int | None = None,
    ) -> AssessmentWithQuestionsResponse:
        """Link an existing question to an assessment.

        Args:
            user_id: User UUID
            assessment_id: Assessment UUID
            question_id: Question UUID
            order: Order position for the question

        Returns:
            Updated assessment with questions

        Raises:
            ResourceNotFoundError: If assessment or question not found
            DuplicateResourceError: If question already linked to assessment
            ValidationError: If order is invalid
            UnauthorizedAccessError: If user doesn't own resources
        """
        # Verify assessment exists and ownership
        assessment = await self.get_owned_assessment(user_id, assessment_id)

        # Verify question exists and ownership
        await self.question_svc.get_owned_question(user_id, question_id)

        # Check for existing association
        existing_assoc = await self.assoc_repo.find_association(
            assessment_id, question_id
        )
        if existing_assoc:
            raise DuplicateResourceError(
                "AssessmentQuestion",
                "question_id/assessment_id",
                f"assessment={assessment_id}, question={question_id}",
            )

        # Validate and determine order
        current_count = await self.assoc_repo.get_count(assessment_id)

        if order is not None and (order < 0 or order > current_count):
            raise ValidationError(
                f"Order must be between 0 and {current_count}. "
                "Omit order to append to the end."
            )

        if order is None:
            order = current_count

        if order < current_count:
            await self.assoc_repo.shift_orders_from(assessment_id, order)

        # Create association
        assoc = AssessmentQuestion(
            assessment_id=assessment_id,
            question_id=question_id,
            order=order,
        )
        await self.assoc_repo.create(assoc)

        # Expire the cached assessment to force fresh query
        self.assessment_repo.db.expire(assessment)

        # Return updated assessment with questions
        return await self.get_assessment_with_questions(user_id, assessment_id)

    async def remove_question_from_assessment(
        self,
        user_id: UUID,
        assessment_id: UUID,
        question_id: UUID,
    ) -> None:
        """Remove a question from an assessment and clean up if orphaned.

        Args:
            user_id: User UUID
            assessment_id: Assessment UUID
            question_id: Question UUID

        Raises:
            ResourceNotFoundError: If association not found
            UnauthorizedAccessError: If user doesn't own the assessment
        """
        assessment = await self.get_owned_assessment(user_id, assessment_id)

        assoc = await self.assoc_repo.find_association(assessment_id, question_id)
        if not assoc:
            raise ResourceNotFoundError(
                "AssessmentQuestion",
                f"assessment={assessment_id}, question={question_id}",
            )

        await self.assoc_repo.hard_delete(assoc)
        await self.assoc_repo.normalize_orders(assessment_id)
        await self.question_svc.cleanup_orphaned_questions(assessment.owner_id)

    async def reorder_questions(
        self,
        user_id: UUID,
        assessment_id: UUID,
        question_orders: list[QuestionOrder],
    ) -> AssessmentWithQuestionsResponse:
        """Reorder questions in an assessment.

        Args:
            user_id: User UUID
            assessment_id: Assessment UUID
            question_orders: List of QuestionOrder objects with question_id and order

        Returns:
            Updated assessment with questions

        Raises:
            ResourceNotFoundError: If assessment not found
            ValidationError: If not all questions are included in reorder
            UnauthorizedAccessError: If user doesn't own the assessment
        """
        # Verify assessment exists and ownership
        await self.get_owned_assessment(user_id, assessment_id)

        # Get all current associations
        current_assocs = await self.assoc_repo.get_all_for_assessment(assessment_id)
        current_question_ids = {assoc.question_id for assoc in current_assocs}

        # Check that ALL questions are included
        requested_question_ids = {item.question_id for item in question_orders}
        if current_question_ids != requested_question_ids:
            raise ValidationError(
                "Reorder must include ALL questions in the assessment."
            )

        # Sort by the requested order to determine final sequence
        sorted_orders = sorted(question_orders, key=lambda x: x.order)

        # Temporarily offset all orders to avoid constraint violations
        assoc: AssessmentQuestion | None = None
        for assoc in current_assocs:
            assoc.order = -(assoc.order + 1)
            await self.assoc_repo.update(assoc)

        # Flush to commit temporary offsets
        await self.assessment_repo.db.flush()

        # Apply final normalized orders (0, 1, 2, 3...)
        for idx, item in enumerate(sorted_orders):
            assoc = await self.assoc_repo.find_association(
                assessment_id, item.question_id
            )
            if assoc:
                assoc.order = idx
                await self.assoc_repo.update(assoc)

        # Flush updates
        await self.assessment_repo.db.flush()

        # Return updated assessment with questions
        return await self.get_assessment_with_questions(user_id, assessment_id)
