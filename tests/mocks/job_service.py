"""Mock JobService that executes jobs inline in tests without Nomad."""

import json
from typing import Any
from uuid import UUID

from edcraft_engine.question_generator.models import (
    ExecutionSpec,
    GenerationOptions,
    QuestionSpec,
)
from sqlalchemy.ext.asyncio import AsyncSession

from edcraft_backend.models import Job, JobStatus, JobType
from edcraft_backend.models.enums import TextTemplateType
from edcraft_backend.repositories import (
    AssessmentQuestionRepository,
    AssessmentRepository,
    AssessmentTemplateQuestionTemplateRepository,
    AssessmentTemplateRepository,
    FolderRepository,
    JobRepository,
    JobTokenRepository,
    QuestionBankQuestionRepository,
    QuestionBankRepository,
    QuestionRepository,
    QuestionTemplateBankQuestionTemplateRepository,
    QuestionTemplateBankRepository,
    QuestionTemplateRepository,
    TargetElementRepository,
)
from edcraft_backend.schemas import AssessmentMetadata
from edcraft_backend.services import (
    AssessmentService,
    AssessmentTemplateService,
    CodeAnalysisService,
    FolderService,
    FormBuilderService,
    InputGeneratorService,
    JobService,
    QuestionGenerationService,
    QuestionService,
    QuestionTemplateService,
)
from tests.mocks.engine import MockQuestionGenerator, MockStaticAnalyser


class MockJobService:
    """Executes jobs inline in tests without Nomad."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.job_repo = JobRepository(db)
        self.job_token_repo = JobTokenRepository(db)
        self._question_gen_svc: Any = None

    def _get_question_gen_svc(self) -> Any:
        if self._question_gen_svc is not None:
            return self._question_gen_svc

        db = self.db
        folder_repo = FolderRepository(db)
        assessment_repo = AssessmentRepository(db)
        question_repo = QuestionRepository(db)
        question_template_repo = QuestionTemplateRepository(db)
        target_element_repo = TargetElementRepository(db)
        assessment_question_repo = AssessmentQuestionRepository(db)
        assessment_template_repo = AssessmentTemplateRepository(db)
        assoc_repo = AssessmentTemplateQuestionTemplateRepository(db)
        question_bank_repo = QuestionBankRepository(db)
        question_bank_question_repo = QuestionBankQuestionRepository(db)
        qt_bank_repo = QuestionTemplateBankRepository(db)
        qt_bank_qt_repo = QuestionTemplateBankQuestionTemplateRepository(db)

        question_svc = QuestionService(
            question_repo, assessment_question_repo, question_bank_question_repo
        )
        question_template_svc = QuestionTemplateService(
            question_template_repo, assoc_repo, target_element_repo, qt_bank_qt_repo
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
        assessment_svc = AssessmentService(
            assessment_repo, folder_svc, assessment_question_repo, question_svc
        )
        assessment_template_svc = AssessmentTemplateService(
            assessment_template_repo, folder_svc, question_template_svc, assoc_repo
        )
        svc = QuestionGenerationService(
            question_template_svc, assessment_template_svc, assessment_svc
        )
        svc.question_generator = MockQuestionGenerator()
        self._question_gen_svc = svc
        return svc

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

        try:
            result = await self._execute(job_type, params)
            result_json = json.dumps(result, default=str)
            await self.job_repo.complete(job.id, result_json, None)
        except Exception as exc:
            await self.job_repo.complete(job.id, None, str(exc))

        await self.db.refresh(job)
        return job

    async def _execute(self, job_type: JobType, params: dict[str, Any]) -> Any:
        import codecs

        if job_type == JobType.ANALYSE_CODE:
            decoded = codecs.decode(params["code"], "unicode_escape")
            svc = CodeAnalysisService()
            svc.static_analyser = MockStaticAnalyser()
            code_info = svc.analyse_code(decoded)
            form_elements = FormBuilderService().build_form_elements()
            return {
                "code_info": code_info.model_dump(),
                "form_elements": [e.model_dump() for e in form_elements],
            }

        if job_type == JobType.GENERATE_QUESTION:
            decoded = codecs.decode(params["code"], "unicode_escape")
            result = await self._get_question_gen_svc().generate_question(
                code=decoded,
                question_spec=QuestionSpec(**params["question_spec"]),
                execution_spec=ExecutionSpec(**params["execution_spec"]),
                generation_options=GenerationOptions(**params["generation_options"]),
            )
            return result.model_dump()

        if job_type == JobType.GENERATE_TEMPLATE:
            decoded = codecs.decode(params["code"], "unicode_escape")
            result = await self._get_question_gen_svc().generate_template(
                code=decoded,
                entry_function=params["entry_function"],
                question_spec=QuestionSpec(**params["question_spec"]),
                generation_options=GenerationOptions(**params["generation_options"]),
                text_template_type=TextTemplateType(params["text_template_type"]),
                question_text_template=params.get("question_text_template"),
            )
            return result.model_dump(mode="json")

        if job_type == JobType.QUESTION_FROM_TEMPLATE:
            result = await self._get_question_gen_svc().generate_question_from_template(
                user_id=UUID(params["user_id"]),
                template_id=UUID(params["template_id"]),
                input_data=params["input_data"],
            )
            return result.model_dump()

        if job_type == JobType.ASSESSMENT_FROM_TEMPLATE:
            result = (
                await self._get_question_gen_svc().generate_assessment_from_template(
                    user_id=UUID(params["user_id"]),
                    template_id=UUID(params["template_id"]),
                    assessment_metadata=AssessmentMetadata(
                        **params["assessment_metadata"]
                    ),
                    question_inputs=params["question_inputs"],
                )
            )
            await self.db.commit()
            return result.model_dump()

        if job_type == JobType.GENERATE_INPUTS:
            result = InputGeneratorService().generate_inputs(params["inputs"])
            return {"inputs": result}

        raise ValueError(f"Unknown job type: {job_type!r}")

    async def get_job(self, job_id: UUID, user_id: UUID | None = None) -> Job:
        real = JobService(self.job_repo, self.job_token_repo, executor=None)
        return await real.get_job(job_id, user_id)

    async def on_callback(
        self,
        token: str,
        result_json: str | None,
        error: str | None,
    ) -> None:
        real = JobService(self.job_repo, self.job_token_repo, executor=None)
        await real.on_callback(token, result_json, error)
