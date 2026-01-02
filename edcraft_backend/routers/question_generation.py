import codecs

from edcraft_engine.question_generator.models import Question as EngineQuestion
from fastapi import APIRouter, Depends, status

from edcraft_backend.exceptions import (
    CodeAnalysisError,
    CodeDecodingError,
    QuestionGenerationError,
)
from edcraft_backend.schemas.question_generation import (
    CodeAnalysisRequest,
    CodeAnalysisResponse,
    QuestionGenerationRequest,
)
from edcraft_backend.services.code_analysis import CodeAnalysisService
from edcraft_backend.services.form_builder import FormBuilderService
from edcraft_backend.services.question_generation import QuestionGenerationService

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
    svc: QuestionGenerationService = Depends(QuestionGenerationService),
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
        return svc.generate_question(
            code=decoded_code,
            question_spec=request.question_spec,
            execution_spec=request.execution_spec,
            generation_options=request.generation_options,
        )
    except Exception as e:
        raise QuestionGenerationError(f"Question generation failed: {str(e)}") from e
