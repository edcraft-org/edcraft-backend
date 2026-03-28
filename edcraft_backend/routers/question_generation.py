import codecs
from uuid import UUID

from fastapi import APIRouter, status

from edcraft_backend.dependencies import (
    AssessmentTemplateServiceDep,
    CurrentUserDep,
    JobServiceDep,
    QuestionTemplateServiceDep,
)
from edcraft_backend.models.job import JobType
from edcraft_backend.schemas.job import JobSubmittedResponse
from edcraft_backend.schemas.question_generation import (
    CodeAnalysisRequest,
    GenerateAssessmentFromTemplateRequest,
    GenerateQuestionFromTemplateRequest,
    GenerateTemplateRequest,
    QuestionGenerationRequest,
)
from edcraft_backend.utils.code_parser import parse_function_parameters

router = APIRouter(prefix="/question-generation", tags=["question-generation"])


def _serialize_target_elements(target_elements: list) -> list[dict]:
    return [
        {
            "element_type": el.element_type.value,
            "id_list": el.id_list,
            "name": el.name,
            "line_number": el.line_number,
            "modifier": el.modifier.value if el.modifier else None,
            "argument_keys": el.argument_keys,
        }
        for el in target_elements
    ]


@router.post(
    "/analyse-code",
    response_model=JobSubmittedResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def analyse_code(
    request: CodeAnalysisRequest,
    job_service: JobServiceDep,
) -> JobSubmittedResponse:
    """Submit a code analysis job. Poll GET /jobs/{job_id} for the result."""
    job = await job_service.submit(
        job_type=JobType.ANALYSE_CODE,
        params={"code": request.code},
        user_id=None,
    )
    return JobSubmittedResponse(job_id=job.id, status_url=f"/jobs/{job.id}")


@router.post(
    "/generate-question",
    response_model=JobSubmittedResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def generate_question(
    request: QuestionGenerationRequest,
    job_service: JobServiceDep,
) -> JobSubmittedResponse:
    """Submit a question generation job. Poll GET /jobs/{job_id} for the result."""
    job = await job_service.submit(
        job_type=JobType.GENERATE_QUESTION,
        params=request.model_dump(),
        user_id=None,
    )
    return JobSubmittedResponse(job_id=job.id, status_url=f"/jobs/{job.id}")


@router.post(
    "/generate-template",
    response_model=JobSubmittedResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def generate_template_preview(
    request: GenerateTemplateRequest,
    job_service: JobServiceDep,
) -> JobSubmittedResponse:
    """Submit a template preview generation job. Poll GET /jobs/{job_id} for the result."""
    try:
        decoded_code = codecs.decode(request.code, "unicode_escape")
        func_params = parse_function_parameters(
            decoded_code, request.execution_spec.entry_function
        ).parameters
    except (ValueError, UnicodeDecodeError):
        func_params = []
    params = request.model_dump()
    params["func_params"] = func_params

    job = await job_service.submit(
        job_type=JobType.GENERATE_TEMPLATE,
        params=params,
        user_id=None,
    )
    return JobSubmittedResponse(job_id=job.id, status_url=f"/jobs/{job.id}")


@router.post(
    "/from-template/{template_id}",
    response_model=JobSubmittedResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def generate_question_from_template(
    user: CurrentUserDep,
    template_id: UUID,
    request: GenerateQuestionFromTemplateRequest,
    job_service: JobServiceDep,
    question_template_svc: QuestionTemplateServiceDep,
) -> JobSubmittedResponse:
    """Submit a question-from-template job. Poll GET /jobs/{job_id} for the result."""
    template = await question_template_svc.get_template(user.id, template_id)

    job = await job_service.submit(
        job_type=JobType.QUESTION_FROM_TEMPLATE,
        params={
            "code": template.code,
            "question_type": template.question_type.value,
            "output_type": template.output_type.value,
            "num_distractors": template.num_distractors,
            "entry_function": template.entry_function,
            "question_text_template": template.question_text_template,
            "text_template_type": template.text_template_type.value,
            "target_elements": _serialize_target_elements(template.target_elements),
            "input_data": request.input_data,
        },
        user_id=user.id,
    )
    return JobSubmittedResponse(job_id=job.id, status_url=f"/jobs/{job.id}")


@router.post(
    "/assessment-from-template/{template_id}",
    response_model=JobSubmittedResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def generate_assessment_from_template(
    user: CurrentUserDep,
    template_id: UUID,
    request: GenerateAssessmentFromTemplateRequest,
    job_service: JobServiceDep,
    assessment_template_svc: AssessmentTemplateServiceDep,
) -> JobSubmittedResponse:
    """Submit an assessment-from-template job. Poll GET /jobs/{job_id} for the result."""
    assessment_template = await assessment_template_svc.get_template_with_question_templates(
        user.id, template_id
    )

    meta = request.assessment_metadata
    resolved_folder_id = str(meta.folder_id or assessment_template.folder_id)
    resolved_title = meta.title or assessment_template.title
    resolved_description = meta.description or assessment_template.description

    question_templates = [
        {
            "id": str(qt.id),
            "code": qt.code,
            "question_type": qt.question_type,
            "output_type": qt.output_type,
            "num_distractors": qt.num_distractors,
            "entry_function": qt.entry_function,
            "question_text_template": qt.question_text_template,
            "text_template_type": qt.text_template_type.value,
            "target_elements": _serialize_target_elements(qt.target_elements),
        }
        for qt in assessment_template.question_templates
    ]

    job = await job_service.submit(
        job_type=JobType.ASSESSMENT_FROM_TEMPLATE,
        params={
            "user_id": str(user.id),
            "assessment_metadata": {
                "folder_id": resolved_folder_id,
                "title": resolved_title,
                "description": resolved_description,
            },
            "question_templates": question_templates,
            "question_inputs": request.question_inputs,
        },
        user_id=user.id,
    )
    return JobSubmittedResponse(job_id=job.id, status_url=f"/jobs/{job.id}")
