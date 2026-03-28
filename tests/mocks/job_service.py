"""Mock JobService that executes jobs inline in tests without Nomad."""

import json
from typing import Any
from uuid import UUID

from input_gen import generate
from sqlalchemy.ext.asyncio import AsyncSession

from edcraft_backend.models.job import Job, JobStatus, JobType
from edcraft_backend.repositories.assessment_repository import AssessmentRepository
from edcraft_backend.repositories.assessment_template_repository import (
    AssessmentTemplateRepository,
)
from edcraft_backend.repositories.folder_repository import FolderRepository
from edcraft_backend.repositories.job_repository import (
    JobRepository,
    JobTokenRepository,
)
from edcraft_backend.repositories.question_bank_repository import QuestionBankRepository
from edcraft_backend.repositories.question_repository import QuestionRepository
from edcraft_backend.repositories.question_template_bank_repository import (
    QuestionTemplateBankRepository,
)
from edcraft_backend.repositories.question_template_repository import (
    QuestionTemplateRepository,
)
from edcraft_backend.repositories.resource_collaborator_repository import (
    ResourceCollaboratorRepository,
)
from edcraft_backend.repositories.target_element_repository import (
    TargetElementRepository,
)
from edcraft_backend.repositories.user_repository import UserRepository
from edcraft_backend.services.assessment_service import AssessmentService
from edcraft_backend.services.collaboration_service import CollaborationService
from edcraft_backend.services.folder_service import FolderService
from edcraft_backend.services.form_builder_service import FormBuilderService
from edcraft_backend.services.job_service import JobService
from edcraft_backend.services.post_processing_service import PostProcessingService
from edcraft_backend.services.question_service import QuestionService
from edcraft_backend.services.question_template_service import QuestionTemplateService
from tests.mocks.engine import MockQuestionGenerator, MockStaticAnalyser
from worker.handlers import JobHandlers


class MockJobService:
    """Executes jobs inline in tests without Nomad.

    Mirrors the worker + JobService.on_callback flow, using mock engine
    components and running everything synchronously in the test transaction.
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.job_repo = JobRepository(db)
        self.job_token_repo = JobTokenRepository(db)
        self._handlers = JobHandlers(
            question_generator=MockQuestionGenerator(),
            static_analyser=MockStaticAnalyser(),
            generate_input=generate,
        )
        self._post_processing_svc = self._build_post_processing_svc(db)

    @staticmethod
    def _build_post_processing_svc(db: AsyncSession) -> PostProcessingService:
        collaborator_repo = ResourceCollaboratorRepository(db)
        question_repo = QuestionRepository(db)
        question_template_repo = QuestionTemplateRepository(db)
        target_element_repo = TargetElementRepository(db)
        folder_repo = FolderRepository(db)
        assessment_repo = AssessmentRepository(db)
        question_bank_repo = QuestionBankRepository(db)
        qt_bank_repo = QuestionTemplateBankRepository(db)
        assessment_template_repo = AssessmentTemplateRepository(db)
        user_repo = UserRepository(db)

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
            assessment_repo,
            folder_svc,
            question_svc,
            user_repo,
            collaboration_svc,
        )
        return PostProcessingService(assessment_svc, FormBuilderService())

    async def submit(
        self,
        job_type: JobType,
        params: dict[str, Any],
        user_id: UUID | None = None,
    ) -> Job:
        job = Job(type=job_type.value, status=JobStatus.QUEUED.value, user_id=user_id)
        self.db.add(job)
        await self.db.flush()
        await self.db.refresh(job)

        result_json: str | None = None
        error: str | None = None

        try:
            raw = self._handlers.dispatch(job_type.value, params)
            processed = await self._post_process(job_type.value, raw)
            result_json = json.dumps(processed, default=str)
        except Exception as exc:
            error = str(exc)

        await self.job_repo.complete(job.id, result_json, error)
        await self.db.refresh(job)
        return job

    async def _post_process(self, job_type: str, raw: dict[str, Any]) -> dict[str, Any]:
        if job_type == JobType.ANALYSE_CODE:
            return self._post_processing_svc.post_process_code_analysis(raw)
        if job_type == JobType.GENERATE_TEMPLATE:
            return self._post_processing_svc.post_process_generate_template(raw)
        if job_type == JobType.QUESTION_FROM_TEMPLATE:
            return self._post_processing_svc.post_process_question_from_template(raw)
        if job_type == JobType.ASSESSMENT_FROM_TEMPLATE:
            return (
                await self._post_processing_svc.post_process_assessment_from_template(
                    raw
                )
            )
        return raw

    async def get_job(self, job_id: UUID, user_id: UUID | None = None) -> Job:
        return await JobService(
            self.job_repo,
            self.job_token_repo,
            executor=None,
            post_processing_svc=self._post_processing_svc,
        ).get_job(job_id, user_id)

    async def on_callback(
        self,
        token: str,
        result_json: str | None,
        error: str | None,
    ) -> None:
        await JobService(
            self.job_repo,
            self.job_token_repo,
            executor=None,
            post_processing_svc=self._post_processing_svc,
        ).on_callback(token, result_json, error)
