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
from edcraft_backend.models.enums import (
    TargetElementType,
    TargetModifier,
    TextTemplateType,
)
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
from edcraft_backend.schemas.question_generation import (
    AssessmentMetadata,
    TemplatePreviewResponse,
)
from edcraft_backend.schemas.question_template import CreateTargetElementRequest
from edcraft_backend.services.assessment_template_service import (
    AssessmentTemplateService,
)
from edcraft_backend.utils.code_parser import parse_function_parameters
from edcraft_backend.utils.template_renderer import render_question_text

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

        question = await self.generate_question(
            code=template.code,
            question_spec=question_spec,
            execution_spec=execution_spec,
            generation_options=generation_options,
        )

        rendered_text = render_question_text(
            template.question_text_template,
            template.text_template_type,
            input_data,
        )
        return question.model_copy(update={"text": rendered_text})

    async def generate_template(
        self,
        code: str,
        entry_function: str,
        question_spec: QuestionSpec,
        generation_options: GenerationOptions,
        text_template_type: TextTemplateType,
        question_text_template: str | None = None,
    ) -> TemplatePreviewResponse:
        """Generate template data including preview question and text template."""
        preview_question = self.question_generator.generate_template_preview(
            question_spec=question_spec,
            generation_options=generation_options,
        )

        if question_text_template is None:
            func_params = parse_function_parameters(code, entry_function)
            if func_params.parameters:
                input_fmt = ", ".join(f"{p} = {{{p}}}" for p in func_params.parameters)
                question_text_template = (
                    f"{preview_question.text}\nGiven input: {input_fmt}"
                )
            else:
                question_text_template = preview_question.text

        target_elements = [
            CreateTargetElementRequest(
                element_type=TargetElementType(e.type),
                id_list=e.id,
                name=e.name,
                line_number=e.line_number,
                modifier=TargetModifier(e.modifier) if e.modifier else None,
            )
            for e in question_spec.target
        ]

        return TemplatePreviewResponse(
            question_text_template=question_text_template,
            text_template_type=text_template_type,
            question_type=preview_question.question_type,
            preview_question=preview_question,
            code=code,
            entry_function=entry_function,
            output_type=question_spec.output_type,
            num_distractors=generation_options.num_distractors,
            target_elements=target_elements,
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
