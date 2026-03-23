"""Nomad worker entrypoint.

Run as: python -m worker.entrypoint

Reads job type and params from environment variables injected by Nomad,
executes the corresponding service logic, then POSTs the result to the
callback URL so FastAPI can store it and mark the job complete.
"""

import asyncio
import base64
import codecs
import json
import logging
import os
from typing import Any, cast
from uuid import UUID

import httpx
from edcraft_engine.question_generator.models import (
    ExecutionSpec,
    GenerationOptions,
    QuestionSpec,
)
from sqlalchemy.ext.asyncio import AsyncSession

from edcraft_backend.config.settings import load_env_files
from edcraft_backend.database import AsyncSessionLocal
from edcraft_backend.models.enums import TextTemplateType
from edcraft_backend.repositories import (
    AssessmentRepository,
    AssessmentTemplateRepository,
    FolderRepository,
    QuestionBankRepository,
    QuestionRepository,
    QuestionTemplateBankRepository,
    QuestionTemplateRepository,
    ResourceCollaboratorRepository,
    TargetElementRepository,
    UserRepository,
)
from edcraft_backend.schemas import AssessmentMetadata
from edcraft_backend.services import (
    AssessmentService,
    AssessmentTemplateService,
    CodeAnalysisService,
    CollaborationService,
    FolderService,
    FormBuilderService,
    InputGeneratorService,
    QuestionGenerationService,
    QuestionService,
    QuestionTemplateService,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s - %(message)s",
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Entry / runner
# ---------------------------------------------------------------------------


def main() -> None:
    job_type = os.environ["EDCRAFT_JOB_TYPE"]
    callback_url = os.environ["EDCRAFT_CALLBACK_URL"]
    params = json.loads(base64.b64decode(os.environ["EDCRAFT_PARAMS_B64"]))

    logger.info("Starting worker for job type: %s", job_type)
    asyncio.run(_run(job_type, params, callback_url))


async def _run(job_type: str, params: dict[str, Any], callback_url: str) -> None:
    result_json: str | None = None
    error: str | None = None

    try:
        # Load environment files so settings are populated (DATABASE_URL, etc.)
        load_env_files()

        result = await _dispatch(job_type, params)
        result_json = json.dumps(result, default=str)
    except Exception as exc:
        logger.exception("Job %s failed", job_type)
        error = str(exc)

    await _post_callback(callback_url, result_json, error)


async def _post_callback(
    url: str,
    result_json: str | None,
    error: str | None,
) -> None:
    payload = {"result": result_json, "error": error}
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
        logger.info("Callback delivered successfully")
    except Exception:
        logger.exception("Failed to deliver callback to %s", url)


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------


async def _dispatch(job_type: str, params: dict[str, Any]) -> Any:
    if job_type == "analyse_code":
        return await _handle_analyse_code(params)
    if job_type == "generate_question":
        return await _handle_generate_question(params)
    if job_type == "generate_template":
        return await _handle_generate_template(params)
    if job_type == "question_from_template":
        return await _handle_question_from_template(params)
    if job_type == "assessment_from_template":
        return await _handle_assessment_from_template(params)
    if job_type == "generate_inputs":
        return _handle_generate_inputs(params)
    raise ValueError(f"Unknown job type: {job_type!r}")


# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------


def _handle_generate_inputs(params: dict[str, Any]) -> dict[str, Any]:
    svc = InputGeneratorService()
    result = svc.generate_inputs(params["inputs"])
    return {"inputs": result}


async def _handle_analyse_code(params: dict[str, Any]) -> dict[str, Any]:
    decoded_code = codecs.decode(params["code"], "unicode_escape")
    code_info = CodeAnalysisService().analyse_code(decoded_code)
    form_elements = FormBuilderService().build_form_elements()
    return {
        "code_info": code_info.model_dump(),
        "form_elements": [e.model_dump() for e in form_elements],
    }


async def _handle_generate_question(params: dict[str, Any]) -> dict[str, Any]:
    async with AsyncSessionLocal() as db:
        decoded_code = codecs.decode(params["code"], "unicode_escape")
        svc = await _build_question_generation_service(db)
        result = await svc.generate_question(
            code=decoded_code,
            question_spec=QuestionSpec(**params["question_spec"]),
            execution_spec=ExecutionSpec(**params["execution_spec"]),
            generation_options=GenerationOptions(**params["generation_options"]),
        )
        return cast(dict[str, Any], result.model_dump())


async def _handle_generate_template(params: dict[str, Any]) -> dict[str, Any]:
    async with AsyncSessionLocal() as db:
        decoded_code = codecs.decode(params["code"], "unicode_escape")
        svc = await _build_question_generation_service(db)
        result = await svc.generate_template(
            code=decoded_code,
            execution_spec=ExecutionSpec(**params["execution_spec"]),
            question_spec=QuestionSpec(**params["question_spec"]),
            generation_options=GenerationOptions(**params["generation_options"]),
            text_template_type=TextTemplateType(params["text_template_type"]),
            question_text_template=params.get("question_text_template"),
        )
        return result.model_dump(mode="json")


async def _handle_question_from_template(params: dict[str, Any]) -> dict[str, Any]:
    async with AsyncSessionLocal() as db:
        svc = await _build_question_generation_service(db)
        result = await svc.generate_question_from_template(
            user_id=UUID(params["user_id"]),
            template_id=UUID(params["template_id"]),
            input_data=params["input_data"],
        )
        return cast(dict[str, Any], result.model_dump())


async def _handle_assessment_from_template(params: dict[str, Any]) -> dict[str, Any]:
    async with AsyncSessionLocal() as db:
        svc = await _build_question_generation_service(db)
        result = await svc.generate_assessment_from_template(
            user_id=UUID(params["user_id"]),
            template_id=UUID(params["template_id"]),
            assessment_metadata=AssessmentMetadata(**params["assessment_metadata"]),
            question_inputs=params["question_inputs"],
        )
        await db.commit()
        return result.model_dump()


async def _build_question_generation_service(db: AsyncSession) -> QuestionGenerationService:
    """Build QuestionGenerationService with its full dependency graph."""
    # Repositories
    folder_repo = FolderRepository(db)
    assessment_repo = AssessmentRepository(db)
    question_repo = QuestionRepository(db)
    question_template_repo = QuestionTemplateRepository(db)
    target_element_repo = TargetElementRepository(db)
    assessment_template_repo = AssessmentTemplateRepository(db)
    question_bank_repo = QuestionBankRepository(db)
    qt_bank_repo = QuestionTemplateBankRepository(db)
    collaborator_repo = ResourceCollaboratorRepository(db)
    user_repo = UserRepository(db)

    # Services
    question_svc = QuestionService(question_repo, collaborator_repo)
    question_template_svc = QuestionTemplateService(
        question_template_repo, target_element_repo, collaborator_repo
    )
    folder_svc = FolderService(
        folder_repo,
        assessment_repo,
        question_bank_repo,
        assessment_template_repo,
        qt_bank_repo,
        question_svc,
        question_template_svc,
    )
    collaboration_svc = CollaborationService(
        collaborator_repo,
        user_repo,
        folder_svc,
        assessment_repo,
        question_bank_repo,
        qt_bank_repo,
        assessment_template_repo,
    )
    assessment_svc = AssessmentService(
        assessment_repo, folder_svc, question_svc, user_repo, collaboration_svc
    )
    assessment_template_svc = AssessmentTemplateService(
        assessment_template_repo,
        folder_svc,
        question_template_svc,
        question_template_repo,
        collaboration_svc,
    )
    return QuestionGenerationService(
        question_template_svc,
        assessment_template_svc,
        assessment_svc,
    )


if __name__ == "__main__":
    main()
