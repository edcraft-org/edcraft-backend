import json
from typing import Any
from uuid import UUID

from edcraft_engine.question_generator import Question

from edcraft_backend.exceptions import QuestionGenerationError
from edcraft_backend.models.enums import (
    TargetElementType,
    TargetModifier,
    TextTemplateType,
)
from edcraft_backend.schemas.assessment import CreateAssessmentRequest
from edcraft_backend.schemas.question import (
    CreateMCQRequest,
    CreateMRQRequest,
    CreateShortAnswerRequest,
    MCQData,
    MRQData,
    ShortAnswerData,
)
from edcraft_backend.schemas.question_generation import TemplatePreviewResponse
from edcraft_backend.schemas.question_template import CreateTargetElementRequest
from edcraft_backend.services.assessment_service import AssessmentService
from edcraft_backend.services.form_builder_service import FormBuilderService
from edcraft_backend.utils.template_renderer import render_question_text


class PostProcessingService:
    """Handles post processing of edcraft engine's output."""

    def __init__(
        self, assessment_svc: AssessmentService, form_builder_svc: FormBuilderService
    ) -> None:
        self.assessment_svc = assessment_svc
        self.form_builder_svc = form_builder_svc

    def post_process_code_analysis(
        self, code_analysis_result: dict[str, Any]
    ) -> dict[str, Any]:
        form_elements = [
            e.model_dump() for e in self.form_builder_svc.build_form_elements()
        ]
        return {
            "code_info": code_analysis_result["code_info"],
            "form_elements": form_elements,
        }

    def post_process_generate_template(
        self,
        template_generation_result: dict[str, Any],
    ) -> dict[str, Any]:
        question_text_template: str = template_generation_result[
            "question_text_template"
        ]
        text_template_type = TextTemplateType(
            template_generation_result["text_template_type"]
        )
        input_data: dict[str, Any] | None = template_generation_result.get("input_data")

        preview_question_data: dict[str, Any] = dict(
            template_generation_result["preview_question"]
        )
        preview_question_data["text"] = question_text_template
        if input_data is not None:
            preview_question_data["text"] = render_question_text(
                question_text_template, text_template_type, input_data
            )

        target_elements = [
            CreateTargetElementRequest(
                element_type=TargetElementType(te["type"]),
                id_list=te["id"],
                name=te.get("name"),
                line_number=te.get("line_number"),
                modifier=TargetModifier(te["modifier"]) if te.get("modifier") else None,
                argument_keys=te.get("argument_keys"),
            )
            for te in template_generation_result["question_spec"]["target"]
        ]

        response = TemplatePreviewResponse(
            question_text_template=question_text_template,
            text_template_type=text_template_type,
            question_type=preview_question_data["question_type"],
            preview_question=Question.model_validate(preview_question_data),
            code=template_generation_result["code"],
            entry_function=template_generation_result["entry_function"],
            output_type=template_generation_result["output_type"],
            num_distractors=template_generation_result["num_distractors"],
            target_elements=target_elements,
        )
        return response.model_dump(mode="json")

    def post_process_question_from_template(
        self, result: dict[str, Any]
    ) -> dict[str, Any]:
        question = dict(result["question"])
        rendered_text = render_question_text(
            template=result["question_text_template"],
            template_type=TextTemplateType(result["text_template_type"]),
            input_data=result["input_data"],
        )
        question["text"] = rendered_text
        return question

    async def post_process_assessment_from_template(
        self,
        assessment_output: dict[str, Any],
    ) -> dict[str, Any]:
        user_id = UUID(assessment_output["user_id"])
        meta = assessment_output["assessment_metadata"]

        assessment_create = CreateAssessmentRequest(
            folder_id=UUID(meta["folder_id"]),
            title=meta["title"],
            description=meta.get("description"),
        )
        assessment = await self.assessment_svc.create_assessment(
            user_id, assessment_create
        )

        try:
            for q_data in assessment_output["questions"]:
                rendered_text = render_question_text(
                    template=q_data["question_text_template"],
                    template_type=TextTemplateType(q_data["text_template_type"]),
                    input_data=q_data.get("input_data") or {},
                )
                question = q_data["question"]
                question_type = question["question_type"]
                template_id = (
                    UUID(q_data["template_id"]) if q_data.get("template_id") else None
                )

                question_create: (
                    CreateMCQRequest | CreateMRQRequest | CreateShortAnswerRequest
                )
                if question_type == "mcq":
                    serialized_options = [
                        json.dumps(opt) if not isinstance(opt, str) else opt
                        for opt in question["options"]
                    ]
                    question_create = CreateMCQRequest(
                        template_id=template_id,
                        question_text=rendered_text,
                        data=MCQData(
                            options=serialized_options,
                            correct_index=question["correct_indices"][0],
                        ),
                    )
                elif question_type == "mrq":
                    serialized_options = [
                        json.dumps(opt) if not isinstance(opt, str) else opt
                        for opt in question["options"]
                    ]
                    question_create = CreateMRQRequest(
                        template_id=template_id,
                        question_text=rendered_text,
                        data=MRQData(
                            options=serialized_options,
                            correct_indices=question["correct_indices"],
                        ),
                    )
                elif question_type == "short_answer":
                    question_create = CreateShortAnswerRequest(
                        template_id=template_id,
                        question_text=rendered_text,
                        data=ShortAnswerData(correct_answer=question["answer"]),
                    )
                else:
                    raise QuestionGenerationError(
                        f"Unknown question type: {question_type}"
                    )

                await self.assessment_svc.add_question_to_assessment(
                    user_id=user_id,
                    assessment_id=assessment.id,
                    question=question_create,
                )

        except Exception as exc:
            await self.assessment_svc.soft_delete_assessment(user_id, assessment.id)
            raise QuestionGenerationError(
                f"Failed to generate assessment: {exc}"
            ) from exc

        result = await self.assessment_svc.get_assessment_with_questions(
            user_id, assessment.id
        )
        return result.model_dump(mode="json")
