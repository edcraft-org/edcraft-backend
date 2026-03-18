from typing import Literal, cast
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
from edcraft_backend.models.enums import (
    CollaboratorRole,
    ResourceType,
    ResourceVisibility,
)
from edcraft_backend.models.question import Question
from edcraft_backend.models.question_data import MCQData, MRQData
from edcraft_backend.models.resource_collaborator import ResourceCollaborator
from edcraft_backend.repositories.assessment_question_repository import (
    AssessmentQuestionRepository,
)
from edcraft_backend.repositories.assessment_repository import AssessmentRepository
from edcraft_backend.repositories.resource_collaborator_repository import (
    ResourceCollaboratorRepository,
)
from edcraft_backend.repositories.user_repository import UserRepository
from edcraft_backend.schemas.assessment import (
    AssessmentMCQResponse,
    AssessmentMRQResponse,
    AssessmentQuestionResponse,
    AssessmentResponse,
    AssessmentShortAnswerResponse,
    AssessmentWithQuestionsResponse,
    CreateAssessmentRequest,
    QuestionOrder,
    UpdateAssessmentRequest,
)
from edcraft_backend.schemas.question import (
    CreateQuestionRequest,
    UpdateQuestionRequest,
)
from edcraft_backend.schemas.question import (
    MCQData as MCQDataSchema,
)
from edcraft_backend.schemas.question import (
    MRQData as MRQDataSchema,
)
from edcraft_backend.schemas.question import (
    ShortAnswerData as ShortAnswerDataSchema,
)
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
        collaborator_repository: ResourceCollaboratorRepository,
        user_repository: UserRepository,
    ):
        self.assessment_repo = assessment_repository
        self.folder_svc = folder_svc
        self.assoc_repo = assessment_question_repository
        self.question_svc = question_service
        self.collaborator_repo = collaborator_repository
        self.user_repo = user_repository

    async def get_assessment(
        self,
        user_id: UUID,
        assessment_id: UUID,
        min_role: CollaboratorRole = CollaboratorRole.VIEWER,
    ) -> Assessment:
        """Get assessment and verify the user has at least the given role.

        Args:
            user_id: User UUID
            assessment_id: Assessment UUID
            min_role: Minimum required collaborator role

        Returns:
            Assessment entity

        Raises:
            ResourceNotFoundError: If assessment not found
            UnauthorizedAccessError: If user lacks the required role
        """
        assessment = await self.assessment_repo.get_by_id(assessment_id)
        if not assessment:
            raise ResourceNotFoundError("Assessment", str(assessment_id))
        has_perm = await self.collaborator_repo.check_permission(
            ResourceType.ASSESSMENT, assessment_id, user_id, min_role
        )
        if not has_perm:
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
        assessment = await self.assessment_repo.create(assessment)

        collab = ResourceCollaborator(
            resource_type=ResourceType.ASSESSMENT,
            resource_id=assessment.id,
            user_id=user_id,
            role=CollaboratorRole.OWNER,
        )
        await self.collaborator_repo.create(collab)

        return assessment

    async def list_assessments(
        self,
        user_id: UUID,
        folder_id: UUID | None = None,
        collab_filter: Literal["all", "owned", "shared"] = "all",
    ) -> list[AssessmentResponse]:
        """List assessments the user has access to.

        Args:
            user_id: User UUID
            folder_id: Optional folder UUID filter
            collab_filter: "all" (any role), "owned" (owner role only), "shared" (non-owner roles)

        Returns:
            List of AssessmentResponse with my_role populated, ordered by updated_at descending

        Raises:
            ResourceNotFoundError: If folder not found
            UnauthorizedAccessError: If folder does not belong to user (owned filter only)
        """
        if folder_id and collab_filter == "owned":
            await self.folder_svc.get_owned_folder(user_id, folder_id)

        rows = await self.assessment_repo.list_by_collaborator(
            user_id=user_id,
            collab_filter=collab_filter,
            folder_id=folder_id,
        )
        return [
            AssessmentResponse.model_validate(assessment).model_copy(
                update={"my_role": role}
            )
            for assessment, role in rows
        ]

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
            UnauthorizedAccessError: If user lacks editor or owner role
        """
        assessment = await self.get_assessment(
            user_id, assessment_id, min_role=CollaboratorRole.EDITOR
        )
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
        assessment = await self.get_assessment(
            user_id, assessment_id, min_role=CollaboratorRole.OWNER
        )

        assocs = await self.assoc_repo.get_all_for_assessment(assessment.id)
        for assoc in assocs:
            question = await self.question_svc.question_repo.get_by_id(assoc.question_id)
            if question:
                await self.question_svc.question_repo.soft_delete(question)

        deleted_assessment = await self.assessment_repo.soft_delete(assessment)
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
            "linked_from_question_id": q.linked_from_question_id,
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

        is_public = assessment.visibility == ResourceVisibility.PUBLIC
        can_view = is_public
        if not can_view and user_id:
            can_view = await self.collaborator_repo.check_permission(
                ResourceType.ASSESSMENT, assessment_id, user_id, CollaboratorRole.VIEWER
            )

        if not can_view:
            raise ResourceNotFoundError("Assessment", str(assessment_id))

        # Filter out soft-deleted questions
        questions: list[AssessmentQuestionResponse] = []
        for assoc in assessment.question_associations:
            if assoc.question and assoc.question.deleted_at is None:
                question_response = self._build_assessment_question_response(assoc)
                questions.append(question_response)

        my_role = None
        if user_id:
            my_role = await self.collaborator_repo.get_role(
                ResourceType.ASSESSMENT, assessment_id, user_id
            )

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
            my_role=my_role,
        )

    async def _attach_question_to_assessment(
        self,
        assessment: Assessment,
        question_id: UUID,
        order: int | None,
    ) -> None:
        """Validate order, insert the association, and expire the cached assessment."""
        current_count = await self.assoc_repo.get_count(assessment.id)

        if order is not None and (order < 0 or order > current_count):
            raise ValidationError(
                f"Order must be between 0 and {current_count}. "
                "Omit order to append to the end."
            )

        if order is None:
            order = current_count

        if order < current_count:
            await self.assoc_repo.shift_orders_from(assessment.id, order)

        assoc = AssessmentQuestion(
            assessment_id=assessment.id,
            question_id=question_id,
            order=order,
        )
        await self.assoc_repo.create(assoc)
        self.assessment_repo.db.expire(assessment)

    async def _require_assoc_and_question(
        self,
        assessment_id: UUID,
        question_id: UUID,
    ) -> tuple[AssessmentQuestion, Question]:
        """Fetch and validate the assoc + question, raising if either is missing."""
        assoc = await self.assoc_repo.find_association(assessment_id, question_id)
        if not assoc:
            raise ResourceNotFoundError(
                "AssessmentQuestion",
                f"assessment={assessment_id}, question={question_id}",
            )

        question = await self.question_svc.question_repo.get_by_id(question_id)
        if not question:
            raise ResourceNotFoundError("Question", str(question_id))

        return assoc, question

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
            UnauthorizedAccessError: If user lacks editor or owner role
        """
        assessment = await self.get_assessment(
            user_id, assessment_id, min_role=CollaboratorRole.EDITOR
        )
        question_entity = await self.question_svc.create_question(user_id, question)
        await self._attach_question_to_assessment(assessment, question_entity.id, order)
        return await self.get_assessment_with_questions(user_id, assessment_id)

    async def link_question_to_assessment(
        self,
        user_id: UUID,
        assessment_id: UUID,
        question_id: UUID,
        order: int | None = None,
    ) -> AssessmentWithQuestionsResponse:
        """Copy a question into an assessment, and link to source question.

        The user must have at least VIEWER access to the source question (owns it,
        is a collaborator on an assessment containing it, or it's in a public assessment).
        A new independent copy is created and linked to the assessment.

        Args:
            user_id: User UUID
            assessment_id: Assessment UUID
            question_id: UUID of the source question to copy
            order: Order position for the question

        Returns:
            Updated assessment with questions

        Raises:
            ResourceNotFoundError: If assessment or question not found
            ValidationError: If order is invalid
            UnauthorizedAccessError: If user lacks editor/owner role on assessment
                or view access on the source question
        """
        assessment = await self.get_assessment(
            user_id, assessment_id, min_role=CollaboratorRole.EDITOR
        )

        source = await self.question_svc.question_repo.get_by_id(question_id)
        if not source:
            raise ResourceNotFoundError("Question", str(question_id))

        can_view = await self.collaborator_repo.check_question_permission(
            question_id, user_id, CollaboratorRole.VIEWER
        )
        if not can_view:
            raise UnauthorizedAccessError("Question", str(question_id))

        copy = await self.question_svc.copy_question(source, assessment.owner_id)
        await self._attach_question_to_assessment(assessment, copy.id, order)
        return await self.get_assessment_with_questions(user_id, assessment_id)

    async def sync_question_in_assessment(
        self,
        user_id: UUID,
        assessment_id: UUID,
        question_id: UUID,
    ) -> AssessmentWithQuestionsResponse:
        """Sync a linked question's content from its source question.

        Args:
            user_id: User UUID
            assessment_id: Assessment UUID
            question_id: UUID of the question copy in this assessment

        Returns:
            Updated assessment with questions

        Raises:
            ResourceNotFoundError: If assessment, question, or source not found
            ValidationError: If question has no source link
            UnauthorizedAccessError: If user lacks editor/owner role or view access on source
        """
        await self.get_assessment(
            user_id, assessment_id, min_role=CollaboratorRole.EDITOR
        )
        _, question = await self._require_assoc_and_question(assessment_id, question_id)

        if not question.linked_from_question_id:
            raise ValidationError("Question has no source link to sync from.")

        source = await self.question_svc.question_repo.get_by_id(
            question.linked_from_question_id
        )
        if not source:
            raise ResourceNotFoundError(
                "Question", str(question.linked_from_question_id)
            )

        can_view = await self.collaborator_repo.check_question_permission(
            source.id, user_id, CollaboratorRole.VIEWER
        )
        if not can_view:
            raise UnauthorizedAccessError("Question", str(source.id))

        _raw = source.data
        if isinstance(_raw, MCQData):
            _schema_data: MCQDataSchema | MRQDataSchema | ShortAnswerDataSchema = (
                MCQDataSchema.model_validate(_raw)
            )
        elif isinstance(_raw, MRQData):
            _schema_data = MRQDataSchema.model_validate(_raw)
        else:
            _schema_data = ShortAnswerDataSchema.model_validate(_raw)

        update_data = UpdateQuestionRequest(
            question_type=cast(
                Literal["mcq", "mrq", "short_answer"], source.question_type
            ),
            question_text=source.question_text,
            data=_schema_data,
        )
        await self.question_svc._update_question_data(question, update_data)

        return await self.get_assessment_with_questions(user_id, assessment_id)

    async def unlink_question_in_assessment(
        self,
        user_id: UUID,
        assessment_id: UUID,
        question_id: UUID,
    ) -> AssessmentWithQuestionsResponse:
        """Sever the source link on a question without removing it from the assessment.

        Args:
            user_id: User UUID
            assessment_id: Assessment UUID
            question_id: UUID of the question in this assessment

        Returns:
            Updated assessment with questions

        Raises:
            ResourceNotFoundError: If assessment or question not found
            UnauthorizedAccessError: If user lacks editor/owner role
        """
        await self.get_assessment(
            user_id, assessment_id, min_role=CollaboratorRole.EDITOR
        )
        _, question = await self._require_assoc_and_question(assessment_id, question_id)

        question.linked_from_question_id = None
        await self.question_svc.question_repo.update(question)

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
            UnauthorizedAccessError: If user lacks editor or owner role
        """
        await self.get_assessment(
            user_id, assessment_id, min_role=CollaboratorRole.EDITOR
        )
        assoc, question = await self._require_assoc_and_question(
            assessment_id, question_id
        )
        await self.assoc_repo.hard_delete(assoc)
        await self.assoc_repo.normalize_orders(assessment_id)
        await self.question_svc.question_repo.soft_delete(question)

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
            UnauthorizedAccessError: If user lacks editor or owner role
        """
        await self.get_assessment(
            user_id, assessment_id, min_role=CollaboratorRole.EDITOR
        )

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

    async def add_collaborator(
        self,
        caller_id: UUID,
        assessment_id: UUID,
        email: str,
        role: CollaboratorRole,
    ) -> ResourceCollaborator:
        """Add a collaborator to an assessment. Editor or owner.

        Args:
            caller_id: User UUID of the caller (must be editor or owner)
            assessment_id: Assessment UUID
            email: Email address of the user to add
            role: Role to assign (must not be OWNER)

        Returns:
            Created ResourceCollaborator

        Raises:
            UnauthorizedAccessError: If caller lacks editor or owner role
            ValidationError: If role is OWNER
            ResourceNotFoundError: If no user found with given email
            DuplicateResourceError: If user is already a collaborator
        """
        await self.get_assessment(
            caller_id, assessment_id, min_role=CollaboratorRole.EDITOR
        )

        if role == CollaboratorRole.OWNER:
            raise ValidationError(
                "Cannot assign 'owner' role via collaborator management."
            )

        target_user = await self.user_repo.get_by_email(email)
        if not target_user:
            raise ResourceNotFoundError("User", f"email={email}")

        existing = await self.collaborator_repo.find_collaborator(
            ResourceType.ASSESSMENT, assessment_id, target_user.id
        )
        if existing:
            raise DuplicateResourceError(
                "ResourceCollaborator",
                "resource_id/user_id",
                f"assessment={assessment_id}, user={target_user.id}",
            )

        collab = ResourceCollaborator(
            resource_type=ResourceType.ASSESSMENT,
            resource_id=assessment_id,
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
        assessment_id: UUID,
    ) -> list[ResourceCollaborator]:
        """List all collaborators for an assessment. Editor or owner only.

        Args:
            caller_id: User UUID of the caller
            assessment_id: Assessment UUID

        Returns:
            List of ResourceCollaborator rows (with user eagerly loaded)

        Raises:
            UnauthorizedAccessError: If caller lacks editor or owner role
        """
        await self.get_assessment(
            caller_id, assessment_id, min_role=CollaboratorRole.EDITOR
        )
        return await self.collaborator_repo.get_all_for_resource(
            ResourceType.ASSESSMENT, assessment_id
        )

    async def update_collaborator_role(
        self,
        caller_id: UUID,
        assessment_id: UUID,
        collaborator_id: UUID,
        new_role: CollaboratorRole,
    ) -> ResourceCollaborator:
        """Update a collaborator's role. Editor or owner, with restrictions.

        Restrictions:
        - Editors can assign editor or viewer, but not owner
        - Cannot directly change the owner's row (except via ownership transfer)
        - Ownership transfer (new_role=OWNER): owner-only; caller becomes editor

        Args:
            caller_id: User UUID of the caller (must be editor or owner)
            assessment_id: Assessment UUID
            collaborator_id: UUID of the collaborator record to update
            new_role: New role to assign

        Returns:
            Updated ResourceCollaborator

        Raises:
            UnauthorizedAccessError: If caller lacks editor or owner role
            ValidationError: If role constraints are violated
            ResourceNotFoundError: If collaborator not found
        """
        await self.get_assessment(
            caller_id, assessment_id, min_role=CollaboratorRole.EDITOR
        )

        caller_role_raw = await self.collaborator_repo.get_role(
            ResourceType.ASSESSMENT, assessment_id, caller_id
        )
        caller_role = CollaboratorRole(caller_role_raw) if caller_role_raw else None

        collab = await self.collaborator_repo.find_by_id(collaborator_id)
        if not collab or collab.resource_id != assessment_id:
            raise ResourceNotFoundError(
                "ResourceCollaborator",
                f"id={collaborator_id}",
            )

        if new_role == CollaboratorRole.OWNER:
            # Ownership transfer: only the current owner can do this
            if caller_role != CollaboratorRole.OWNER:
                raise ValidationError("Only the owner can transfer ownership.")
            if collab.role == CollaboratorRole.OWNER:
                raise ValidationError("Target user is already the owner.")
            # Demote caller to editor, promote target to owner
            caller_collab = await self.collaborator_repo.find_collaborator(
                ResourceType.ASSESSMENT, assessment_id, caller_id
            )
            if caller_collab:
                caller_collab.role = CollaboratorRole.EDITOR
            collab.role = CollaboratorRole.OWNER
            # Move assessment to the new owner's root folder
            new_owner_root = await self.folder_svc.get_root_folder(collab.user_id)
            assessment = await self.assessment_repo.get_by_id(assessment_id)
            if assessment and new_owner_root:
                assessment.folder_id = new_owner_root.id
            await self.collaborator_repo.db.flush()
            await self.collaborator_repo.db.refresh(collab)
            return collab

        # Cannot directly change the owner's row to a non-owner role
        if collab.role == CollaboratorRole.OWNER:
            raise ValidationError(
                "Cannot change the owner's role directly. Use ownership transfer instead."
            )

        # Editors cannot assign owner (already handled above) — can assign editor or viewer
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
        assessment_id: UUID,
        collaborator_id: UUID,
    ) -> None:
        """Remove a collaborator. Editor or owner; cannot remove the owner.

        Args:
            caller_id: User UUID of the caller (must be editor or owner)
            assessment_id: Assessment UUID
            collaborator_id: UUID of the collaborator record to remove

        Raises:
            UnauthorizedAccessError: If caller lacks editor or owner role
            ValidationError: If trying to remove the owner row
            ResourceNotFoundError: If collaborator not found
        """
        await self.get_assessment(
            caller_id, assessment_id, min_role=CollaboratorRole.EDITOR
        )

        collab = await self.collaborator_repo.find_by_id(collaborator_id)
        if not collab or collab.resource_id != assessment_id:
            raise ResourceNotFoundError(
                "ResourceCollaborator",
                f"id={collaborator_id}",
            )

        if collab.role == CollaboratorRole.OWNER:
            raise ValidationError("Cannot remove the owner.")

        await self.collaborator_repo.hard_delete(collab)
