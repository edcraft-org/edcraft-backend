from typing import TYPE_CHECKING, Any
from uuid import UUID

from edcraft_engine.question_generator.models import (
    ExecutionSpec,
    GenerationOptions,
    Question,
    QuestionSpec,
)
from edcraft_engine.question_generator.question_generator import QuestionGenerator

from edcraft_backend.exceptions import QuestionGenerationError, ValidationError
from edcraft_backend.schemas.assessment import CreateAssessmentRequest
from edcraft_backend.schemas.question import CreateQuestionRequest
from edcraft_backend.schemas.question_generation import AssessmentMetadata
from edcraft_backend.services.assessment_template_service import (
    AssessmentTemplateService,
)

if TYPE_CHECKING:
    from edcraft_backend.schemas.assessment import AssessmentWithQuestionsResponse
    from edcraft_backend.services.assessment_service import AssessmentService
    from edcraft_backend.services.question_template_service import (
        QuestionTemplateService,
    )


class QuestionGenerationService:
    def __init__(
        self,
        question_template_svc: "QuestionTemplateService",
        assessment_template_svc: AssessmentTemplateService,
        assessment_svc: "AssessmentService",
    ) -> None:
        self.question_generator = QuestionGenerator()
        self.question_template_svc = question_template_svc
        self.assessment_template_svc = assessment_template_svc
        self.assessment_svc = assessment_svc

    async def generate_question(
        self,
        code: str,
        question_spec: QuestionSpec,
        execution_spec: ExecutionSpec,
        generation_options: GenerationOptions,
    ) -> Question:

        return self.question_generator.generate_question(
            code=code,
            question_spec=question_spec,
            execution_spec=execution_spec,
            generation_options=generation_options,
        )

    async def generate_question_from_template(
        self,
        user_id: UUID,
        template_id: UUID,
        input_data: dict[str, Any],
    ) -> Question:
        """Generate question from template.

        Args:
            user_id: User UUID
            template_id: QuestionTemplate UUID
            input_data: Input data for executing code

        Returns:
            Generated Question

        Raises:
            QuestionGenerationError: If generation fails
            UnauthorizedAccessError: If user doesn't own the question template
        """
        template = await self.question_template_svc.get_template(user_id, template_id)

        # Extract configuration from template
        config = template.template_config

        code = config.get("code")
        if not code:
            raise ValidationError("Template configuration missing 'code' field.")

        question_spec_dict = config.get("question_spec")
        if not question_spec_dict:
            raise ValidationError(
                "Template configuration missing 'question_spec' field."
            )

        generation_options_dict = config.get("generation_options")
        if not generation_options_dict:
            raise ValidationError(
                "Template configuration missing 'generation_options' field."
            )

        entry_function = config.get("entry_function")
        if not entry_function:
            raise ValidationError(
                "Template configuration missing 'entry_function' field."
            )

        # Create configurations
        question_spec = QuestionSpec(**question_spec_dict)
        execution_spec = ExecutionSpec(
            entry_function=entry_function, input_data=input_data
        )
        generation_options = GenerationOptions(**generation_options_dict)

        return await self.generate_question(
            code=code,
            question_spec=question_spec,
            execution_spec=execution_spec,
            generation_options=generation_options,
        )

    async def create_template_preview(
        self,
        code: str,
        entry_function: str,
        question_spec: QuestionSpec,
        generation_options: GenerationOptions,
    ) -> tuple[Question, dict[str, Any]]:
        """Create template preview without database persistence.

        Args:
            code: Python source code
            entry_function: Name of the entry function
            question_spec: Question specifications
            generation_options: Generation options

        Returns:
            Tuple of (preview_question, template_config)
        """
        preview_question = self.question_generator.generate_template_preview(
            question_spec=question_spec,
            generation_options=generation_options,
        )

        template_config: dict[str, Any] = {
            "code": code,
            "entry_function": entry_function,
            "question_spec": question_spec.model_dump(),
            "generation_options": generation_options.model_dump(),
        }

        return preview_question, template_config

    async def generate_assessment_from_template(
        self,
        user_id: UUID,
        template_id: UUID,
        assessment_metadata: AssessmentMetadata,
        question_inputs: list[dict[str, Any]],
    ) -> "AssessmentWithQuestionsResponse":
        """Generate and persist assessment from assessment template.

        Args:
            user_id: User UUID
            template_id: AssessmentTemplate UUID
            assessment_metadata: Metadata for assessment creation
            question_inputs: List of input data dicts for each question

        Returns:
            Created assessment with questions

        Raises:
            ValidationError: If question_inputs array length doesn't match templates
            QuestionGenerationError: If generation fails
            UnauthorizedAccessError: If user doesn't own the assessment template
        """
        assessment_template = (
            await self.assessment_template_svc.get_template_with_question_templates(
                user_id, template_id
            )
        )

        question_templates = assessment_template.question_templates

        # Validate input array length
        if len(question_inputs) != len(question_templates):
            raise ValidationError(
                f"Expected {len(question_templates)} question inputs, "
                f"got {len(question_inputs)}"
            )

        # Create assessment
        assessment_create = CreateAssessmentRequest(
            folder_id=assessment_metadata.folder_id or assessment_template.folder_id,
            title=assessment_metadata.title or assessment_template.title,
            description=assessment_metadata.description
            or assessment_template.description,
        )
        assessment = await self.assessment_svc.create_assessment(
            user_id, assessment_create
        )

        try:
            # Generate and add questions in order
            for question_template, input_data in zip(
                question_templates, question_inputs, strict=True
            ):
                # Generate question using template
                question = await self.generate_question_from_template(
                    user_id=user_id,
                    template_id=question_template.id,
                    input_data=input_data,
                )

                # Convert generated question to DB question
                additional_data = question.model_dump()
                del additional_data["text"]
                del additional_data["question_type"]

                question_create = CreateQuestionRequest(
                    template_id=question_template.id,
                    question_type=question_template.question_type,
                    question_text=question.text,
                    additional_data=additional_data,
                )

                # Add question to assessment at specific order
                await self.assessment_svc.add_question_to_assessment(
                    user_id=user_id,
                    assessment_id=assessment.id,
                    question=question_create,
                )

        except Exception as e:
            # Rollback by soft-deleting assessment if any question fails
            await self.assessment_svc.soft_delete_assessment(user_id, assessment.id)
            raise QuestionGenerationError(
                f"Failed to generate assessment: {str(e)}"
            ) from e

        # Return complete assessment with questions
        return await self.assessment_svc.get_assessment_with_questions(
            user_id, assessment.id
        )
