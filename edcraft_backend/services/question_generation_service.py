import json
from typing import TYPE_CHECKING, Any
from uuid import UUID

from edcraft_engine.question_generator.models import (
    ExecutionSpec,
    GenerationOptions,
    Question,
    QuestionSpec,
    TargetElement,
)
from edcraft_engine.question_generator.question_generator import QuestionGenerator

from edcraft_backend.exceptions import QuestionGenerationError, ValidationError
from edcraft_backend.schemas.assessment import CreateAssessmentRequest
from edcraft_backend.schemas.question import (
    CreateMCQRequest,
    CreateMRQRequest,
    CreateQuestionRequest,
    CreateShortAnswerRequest,
    MCQData,
    MRQData,
    ShortAnswerData,
)
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

        # Create configurations
        target_elements = [
            TargetElement(
                type=element.element_type.value,
                id=element.id_list,
                name=element.name,
                line_number=element.line_number,
                modifier=element.modifier.value if element.modifier else None,
            )
            for element in template.target_elements
        ]
        question_spec = QuestionSpec(
            question_type=template.question_type.value,
            target=target_elements,
            output_type=template.output_type.value,
        )
        execution_spec = ExecutionSpec(
            entry_function=template.entry_function, input_data=input_data
        )
        generation_options = GenerationOptions(
            num_distractors=template.num_distractors,
        )

        return await self.generate_question(
            code=template.code,
            question_spec=question_spec,
            execution_spec=execution_spec,
            generation_options=generation_options,
        )

    async def create_template_preview(
        self,
        question_spec: QuestionSpec,
        generation_options: GenerationOptions,
    ) -> Question:
        """Create template preview without database persistence.

        Args:
            question_spec: Question specifications
            generation_options: Generation options

        Returns:
            Question preview
        """
        return self.question_generator.generate_template_preview(
            question_spec=question_spec,
            generation_options=generation_options,
        )

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
                question_data = question.model_dump()
                question_text = question_data.pop("text")
                question_type = question_data.pop("question_type")

                # Create the appropriate request type based on question_type
                question_create: CreateQuestionRequest
                if question_type == "mcq":
                    # Serialize options to JSON strings for storage
                    serialized_options = [
                        json.dumps(opt) if not isinstance(opt, str) else opt
                        for opt in question_data["options"]
                    ]
                    question_create = CreateMCQRequest(
                        template_id=question_template.id,
                        question_text=question_text,
                        data=MCQData(
                            options=serialized_options,
                            correct_index=question_data["correct_indices"][0],
                        ),
                    )
                elif question_type == "mrq":
                    # Serialize options to JSON strings for storage
                    serialized_options = [
                        json.dumps(opt) if not isinstance(opt, str) else opt
                        for opt in question_data["options"]
                    ]
                    question_create = CreateMRQRequest(
                        template_id=question_template.id,
                        question_text=question_text,
                        data=MRQData(
                            options=serialized_options,
                            correct_indices=question_data["correct_indices"],
                        ),
                    )
                elif question_type == "short_answer":
                    question_create = CreateShortAnswerRequest(
                        template_id=question_template.id,
                        question_text=question_text,
                        data=ShortAnswerData(
                            correct_answer=question_data["answer"],
                        ),
                    )
                else:
                    raise ValidationError(f"Unknown question type: {question_type}")

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
