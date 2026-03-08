import codecs
from uuid import UUID

from edcraft_engine.question_generator.models import Question as EngineQuestion
from fastapi import APIRouter, Depends, status

from edcraft_backend.dependencies import CurrentUserDep, QuestionGenerationServiceDep
from edcraft_backend.exceptions import (
    CodeAnalysisError,
    CodeDecodingError,
    QuestionGenerationError,
)
from edcraft_backend.models.enums import TargetElementType, TargetModifier
from edcraft_backend.schemas.assessment import AssessmentWithQuestionsResponse
from edcraft_backend.schemas.question_generation import (
    CodeAnalysisRequest,
    CodeAnalysisResponse,
    GenerateAssessmentFromTemplateRequest,
    GenerateQuestionFromTemplateRequest,
    GenerateTemplateRequest,
    QuestionGenerationRequest,
    TemplatePreviewResponse,
)
from edcraft_backend.schemas.question_template import CreateTargetElementRequest
from edcraft_backend.services.code_analysis_service import CodeAnalysisService
from edcraft_backend.services.form_builder_service import FormBuilderService
from edcraft_backend.utils.code_parser import parse_function_parameters

router = APIRouter(prefix="/question-generation", tags=["question-generation"])


@router.post(
    "/analyse-code", response_model=CodeAnalysisResponse, status_code=status.HTTP_200_OK
)
async def analyse_code(
    request: CodeAnalysisRequest,
    code_analysis_svc: CodeAnalysisService = Depends(CodeAnalysisService),
    form_builder_svc: FormBuilderService = Depends(FormBuilderService),
) -> CodeAnalysisResponse:
    """
    Analyse the provided code and generate code information and form schema.

    Args:
        request (CodeAnalysisRequest): The request object containing the code to be analysed.

    Returns:
        CodeAnalysisResponse: The response object containing the code information and form schema.
    """
    try:
        decoded_code = codecs.decode(request.code, "unicode_escape")
    except (UnicodeDecodeError, ValueError) as e:
        raise CodeDecodingError(f"Invalid code format: {str(e)}") from e

    try:
        code_info = code_analysis_svc.analyse_code(decoded_code)
        form_schema = form_builder_svc.build_form_elements()
    except Exception as e:
        raise CodeAnalysisError(f"Code analysis failed: {str(e)}") from e

    return CodeAnalysisResponse(
        code_info=code_info,
        form_elements=form_schema,
    )


@router.post(
    "/generate-question", response_model=EngineQuestion, status_code=status.HTTP_200_OK
)
async def generate_question(
    request: QuestionGenerationRequest,
    service: QuestionGenerationServiceDep,
) -> EngineQuestion:
    """
    Generate a question based on the provided form selections.

    Args:
        request (QuestionGenerationRequest): The request object containing
            the code and specifications.

    Returns:
        Question: The generated question object.
    """
    try:
        decoded_code = codecs.decode(request.code, "unicode_escape")
    except (UnicodeDecodeError, ValueError) as e:
        raise CodeDecodingError(f"Invalid code format: {str(e)}") from e

    try:
        return await service.generate_question(
            code=decoded_code,
            question_spec=request.question_spec,
            execution_spec=request.execution_spec,
            generation_options=request.generation_options,
        )
    except Exception as e:
        raise QuestionGenerationError(f"Question generation failed: {str(e)}") from e


@router.post(
    "/generate-template",
    response_model=TemplatePreviewResponse,
    status_code=status.HTTP_200_OK,
)
async def generate_template_preview(
    request: GenerateTemplateRequest,
    service: QuestionGenerationServiceDep,
) -> TemplatePreviewResponse:
    """
    Create a question template preview without database persistence.

    Args:
        request: Template generation request
        service: Question generation service

    Returns:
        TemplatePreviewResponse with question text template and config

    Raises:
        CodeDecodingError: If code cannot be decoded
        QuestionGenerationError: If template preview generation fails
    """
    try:
        decoded_code = codecs.decode(request.code, "unicode_escape")
    except (UnicodeDecodeError, ValueError) as e:
        raise CodeDecodingError(f"Invalid code format: {str(e)}") from e

    try:
        preview_question = await service.create_template_preview(
            question_spec=request.question_spec,
            generation_options=request.generation_options,
        )
    except Exception as e:
        raise QuestionGenerationError(
            f"Template preview generation failed: {str(e)}"
        ) from e

    if request.question_text_template is not None:
        question_text_template = request.question_text_template
    else:
        params = parse_function_parameters(decoded_code, request.entry_function)
        if params.parameters:
            input_fmt = ", ".join(f"{p} = {{{p}}}" for p in params.parameters)
            question_text_template = (
                f"{preview_question.text}\nGiven input: {input_fmt}"
            )
        else:
            question_text_template = preview_question.text

    return TemplatePreviewResponse(
        question_text_template=question_text_template,
        text_template_type=request.text_template_type,
        question_type=preview_question.question_type,
        preview_question=preview_question,
        code=decoded_code,
        entry_function=request.entry_function,
        output_type=request.question_spec.output_type,
        num_distractors=request.generation_options.num_distractors,
        target_elements=[
            CreateTargetElementRequest(
                element_type=TargetElementType(element.type),
                id_list=element.id,
                name=element.name,
                line_number=element.line_number,
                modifier=TargetModifier(element.modifier) if element.modifier else None,
            )
            for element in request.question_spec.target
        ],
    )


@router.post(
    "/from-template/{template_id}",
    response_model=EngineQuestion,
    status_code=status.HTTP_200_OK,
)
async def generate_question_from_template(
    user: CurrentUserDep,
    template_id: UUID,
    request: GenerateQuestionFromTemplateRequest,
    service: QuestionGenerationServiceDep,
) -> EngineQuestion:
    """Generate a question from a question template."""
    return await service.generate_question_from_template(
        user_id=user.id,
        template_id=template_id,
        input_data=request.input_data,
    )


@router.post(
    "/assessment-from-template/{template_id}",
    response_model=AssessmentWithQuestionsResponse,
    status_code=status.HTTP_201_CREATED,
)
async def generate_assessment_from_template(
    user: CurrentUserDep,
    template_id: UUID,
    request: GenerateAssessmentFromTemplateRequest,
    service: QuestionGenerationServiceDep,
) -> AssessmentWithQuestionsResponse:
    """Generate and persist an assessment from an assessment template."""
    return await service.generate_assessment_from_template(
        user_id=user.id,
        template_id=template_id,
        assessment_metadata=request.assessment_metadata,
        question_inputs=request.question_inputs,
    )
