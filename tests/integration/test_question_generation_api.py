"""Integration tests for Question Generation API endpoints."""

from typing import Any, cast
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from edcraft_backend.models.user import User
from tests.factories import (
    create_assessment_template_with_question_templates,
    create_test_assessment_template,
    create_test_folder,
    create_test_question_template,
)


async def _submit_and_poll(client: AsyncClient, url: str, json: Any) -> dict[str, Any]:
    """Submit a job and poll GET /jobs/{job_id} for the result."""
    resp = await client.post(url, json=json)
    assert resp.status_code == 202
    job_id = resp.json()["job_id"]

    result_resp = await client.get(f"/jobs/{job_id}")
    assert result_resp.status_code == 200
    return cast(dict[str, Any], result_resp.json())


@pytest.mark.integration
@pytest.mark.question_generation
class TestAnalyseCode:
    """Tests for POST /question-generation/analyse-code endpoint."""

    @pytest.mark.asyncio
    async def test_analyse_code_success(self, test_client: AsyncClient) -> None:
        """Test code analysis successfully returns code info and form schema."""
        code_data = {
            "code": "def hello():\\n    print('Hello World')",
        }
        data = await _submit_and_poll(
            test_client, "/question-generation/analyse-code", code_data
        )

        assert data["status"] == "completed"
        result = data["result"]
        assert "code_info" in result
        # Verify code_info structure
        assert "code_tree" in result["code_info"]
        assert "functions" in result["code_info"]
        assert "loops" in result["code_info"]
        assert "branches" in result["code_info"]
        assert "variables" in result["code_info"]

    @pytest.mark.asyncio
    async def test_analyse_code_empty_code(self, test_client: AsyncClient) -> None:
        """Test code analysis with empty code."""
        code_data = {"code": ""}
        data = await _submit_and_poll(
            test_client, "/question-generation/analyse-code", code_data
        )

        assert data["status"] == "completed"
        result = data["result"]
        # Empty code should still return valid structure
        assert "code_info" in result
        # Verify code_info structure
        assert "code_tree" in result["code_info"]
        assert "functions" in result["code_info"]
        assert "loops" in result["code_info"]
        assert "branches" in result["code_info"]
        assert "variables" in result["code_info"]

    @pytest.mark.asyncio
    async def test_analyse_code_with_invalid_encoding(
        self, test_client: AsyncClient
    ) -> None:
        """Test that invalid code encoding causes the job to fail."""
        code_data = {
            "code": "\\x",  # Invalid escape sequence
        }

        data = await _submit_and_poll(
            test_client, "/question-generation/analyse-code", code_data
        )

        assert data["status"] == "failed"
        assert data["error"] is not None


@pytest.mark.integration
@pytest.mark.question_generation
class TestGenerateQuestionFromTemplate:
    """Tests for POST /question-generation/from-template/{template_id} endpoint."""

    @pytest.mark.asyncio
    async def test_generate_question_from_template_success(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test successfully generating a question from a template."""
        # Create user and question template with valid config
        template = await create_test_question_template(
            db_session,
            user,
            question_type="mcq",
            question_text_template="Template question 1? Given input: n = {n}",
            text_template_type="basic",
            code="def example(n):\n    return n * 2",
            entry_function="example",
            num_distractors=4,
            output_type="first",
            target_elements=[
                {
                    "element_type": "function",
                    "id_list": [0],
                    "name": "example",
                    "line_number": 1,
                    "modifier": "return_value",
                }
            ],
        )
        await db_session.commit()

        # Call endpoint with valid input_data
        request_data = {"input_data": {"n": 5}}
        data = await _submit_and_poll(
            test_client,
            f"/question-generation/from-template/{template.id}",
            request_data,
        )

        assert data["status"] == "completed"
        result = data["result"]

        # Verify question structure
        assert "text" in result
        assert "question_type" in result
        assert result["question_type"] == "mcq"
        assert "options" in result
        assert "correct_indices" in result
        assert len(result["options"]) > 0

        # Verify question text correctly incorporates input data
        assert result["text"] == "Template question 1? Given input: n = 5"

    @pytest.mark.asyncio
    async def test_generate_question_from_template_not_found(
        self, test_client: AsyncClient, user: User
    ) -> None:
        """Test generating question from non-existent template returns 404."""
        non_existent_id = uuid4()
        request_data = {"input_data": {"n": 5}}

        resp = await test_client.post(
            f"/question-generation/from-template/{non_existent_id}",
            json=request_data,
        )
        assert resp.status_code == 404



@pytest.mark.integration
@pytest.mark.question_generation
class TestGenerateAssessmentFromTemplate:
    """Tests for POST /question-generation/assessment-from-template/{template_id} endpoint."""

    @pytest.mark.asyncio
    async def test_generate_assessment_from_template_success(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test successfully generating an assessment from a template."""
        # Create user and assessment template with 3 question templates
        assessment_template, question_templates = (
            await create_assessment_template_with_question_templates(
                db_session, user, num_templates=3
            )
        )
        await db_session.commit()

        # Call endpoint with valid assessment_metadata and 3 input_data dicts
        request_data: dict[str, Any] = {
            "assessment_metadata": {
                "owner_id": str(user.id),
                "title": "Custom Assessment",
                "description": "Custom description",
            },
            "question_inputs": [
                {"n": 5},
                {"n": 10},
                {"n": 15},
            ],
        }
        data = await _submit_and_poll(
            test_client,
            f"/question-generation/assessment-from-template/{assessment_template.id}",
            request_data,
        )

        assert data["status"] == "completed"
        result = data["result"]

        # Verify assessment created with correct metadata
        assert result["title"] == "Custom Assessment"
        assert result["description"] == "Custom description"
        assert result["owner_id"] == str(user.id)

        # Verify 3 questions created and linked in correct order
        assert len(result["questions"]) == 3
        for i, question in enumerate(result["questions"]):
            assert question["order"] == i
            assert question["template_id"] == str(question_templates[i].id)

    @pytest.mark.asyncio
    async def test_generate_assessment_from_template_uses_template_defaults(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test assessment uses template defaults when metadata not provided."""
        assessment_template, _ = (
            await create_assessment_template_with_question_templates(
                db_session, user, num_templates=2
            )
        )
        await db_session.commit()

        request_data: dict[str, Any] = {
            "assessment_metadata": {
                "owner_id": str(user.id),
                # No title or description provided
            },
            "question_inputs": [{"n": 5}, {"n": 10}],
        }
        data = await _submit_and_poll(
            test_client,
            f"/question-generation/assessment-from-template/{assessment_template.id}",
            request_data,
        )

        assert data["status"] == "completed"
        result = data["result"]

        assert result["title"] == assessment_template.title
        assert result["description"] == assessment_template.description

    @pytest.mark.asyncio
    async def test_generate_assessment_from_template_overrides_defaults(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test custom metadata overrides template defaults."""
        assessment_template, _ = (
            await create_assessment_template_with_question_templates(
                db_session, user, num_templates=2
            )
        )
        await db_session.commit()

        # Provide custom title and description
        request_data: dict[str, Any] = {
            "assessment_metadata": {
                "owner_id": str(user.id),
                "title": "Override Title",
                "description": "Override Description",
            },
            "question_inputs": [{"n": 5}, {"n": 10}],
        }
        data = await _submit_and_poll(
            test_client,
            f"/question-generation/assessment-from-template/{assessment_template.id}",
            request_data,
        )

        assert data["status"] == "completed"
        result = data["result"]

        assert result["title"] == "Override Title"
        assert result["description"] == "Override Description"

    @pytest.mark.asyncio
    async def test_generate_assessment_from_template_with_folder(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test assessment is created in the specified folder."""
        folder = await create_test_folder(db_session, user)
        assessment_template, _ = (
            await create_assessment_template_with_question_templates(
                db_session, user, num_templates=2
            )
        )
        await db_session.commit()

        request_data: dict[str, Any] = {
            "assessment_metadata": {
                "owner_id": str(user.id),
                "folder_id": str(folder.id),
            },
            "question_inputs": [{"n": 5}, {"n": 10}],
        }
        data = await _submit_and_poll(
            test_client,
            f"/question-generation/assessment-from-template/{assessment_template.id}",
            request_data,
        )

        assert data["status"] == "completed"
        result = data["result"]
        assert result["folder_id"] == str(folder.id)

    @pytest.mark.asyncio
    async def test_generate_assessment_from_template_not_found(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test generating assessment from non-existent template returns 404."""
        await db_session.commit()

        non_existent_id = uuid4()
        request_data: dict[str, Any] = {
            "assessment_metadata": {"owner_id": str(user.id)},
            "question_inputs": [{"n": 5}],
        }

        resp = await test_client.post(
            f"/question-generation/assessment-from-template/{non_existent_id}",
            json=request_data,
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_generate_assessment_from_template_input_count_mismatch(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test input count mismatch causes the job to fail."""
        assessment_template, _ = (
            await create_assessment_template_with_question_templates(
                db_session, user, num_templates=3
            )
        )
        await db_session.commit()

        # Provide only 2 inputs for 3 templates
        request_data: dict[str, Any] = {
            "assessment_metadata": {"owner_id": str(user.id)},
            "question_inputs": [{"n": 5}, {"n": 10}],  # Missing one
        }

        data = await _submit_and_poll(
            test_client,
            f"/question-generation/assessment-from-template/{assessment_template.id}",
            request_data,
        )

        assert data["status"] == "failed"
        error = data["error"].lower()
        assert "expected 3" in error
        assert "got 2" in error

    @pytest.mark.asyncio
    async def test_generate_assessment_from_template_empty_template(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test assessment template with no question templates creates empty assessment."""
        template = await create_test_assessment_template(
            db_session, user, title="Empty Template", description="No questions"
        )
        await db_session.commit()

        request_data: dict[str, Any] = {
            "assessment_metadata": {"owner_id": str(user.id)},
            "question_inputs": [],  # Empty array
        }

        data = await _submit_and_poll(
            test_client,
            f"/question-generation/assessment-from-template/{template.id}",
            request_data,
        )

        assert data["status"] == "completed"
        result = data["result"]
        assert len(result["questions"]) == 0

    @pytest.mark.asyncio
    async def test_generate_assessment_from_template_preserves_question_order(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test questions are created in the same order as templates."""
        assessment_template, question_templates = (
            await create_assessment_template_with_question_templates(
                db_session, user, num_templates=5
            )
        )
        await db_session.commit()

        request_data: dict[str, Any] = {
            "assessment_metadata": {"owner_id": str(user.id)},
            "question_inputs": [{"n": i} for i in range(5)],
        }

        data = await _submit_and_poll(
            test_client,
            f"/question-generation/assessment-from-template/{assessment_template.id}",
            request_data,
        )

        assert data["status"] == "completed"
        result = data["result"]

        assert len(result["questions"]) == 5
        for i in range(5):
            assert result["questions"][i]["order"] == i
            assert result["questions"][i]["template_id"] == str(question_templates[i].id)


@pytest.mark.integration
@pytest.mark.question_generation
class TestGenerateTemplatePreview:
    """Tests for POST /question-generation/generate-template endpoint."""

    @pytest.mark.asyncio
    async def test_generate_template_preview_success(
        self, test_client: AsyncClient
    ) -> None:
        """Test generating template preview with MCQ question type."""
        request_data: dict[str, Any] = {
            "code": "def example(n):\\n    return n * 2",
            "execution_spec": {"entry_function": "example"},
            "question_spec": {
                "target": [
                    {
                        "type": "function",
                        "id": [0],
                        "name": "example",
                        "line_number": 1,
                        "modifier": "return_value",
                    }
                ],
                "output_type": "first",
                "question_type": "mcq",
            },
            "generation_options": {"num_distractors": 4},
        }

        data = await _submit_and_poll(
            test_client, "/question-generation/generate-template", request_data
        )

        assert data["status"] == "completed"
        result = data["result"]

        # Verify response structure
        assert "question_text_template" in result
        assert "text_template_type" in result
        assert "question_type" in result
        assert "preview_question" in result

        # Verify question_type and template type
        assert result["question_type"] == "mcq"
        assert result["text_template_type"] == "basic"

        # Verify question_text_template contains input param placeholders
        assert "Given input: n = {n}" in result["question_text_template"]

        # Verify template_config fields in response
        assert result["code"] == "def example(n):\n    return n * 2"
        assert result["entry_function"] == "example"
        assert result["num_distractors"] == 4
        assert result["output_type"] == "first"
        assert len(result["target_elements"]) == 1

        # Verify preview_question structure
        preview = result["preview_question"]
        assert preview["question_type"] == "mcq"
        assert preview["answer"] == "<placeholder_answer>"
        assert preview["options"] is not None
        assert len(preview["options"]) == 5  # 4 distractors + 1 correct
        assert preview["correct_indices"] == [0]

        # Verify placeholder options format
        for i, option in enumerate(preview["options"]):
            assert option == f"<option_{i+1}>"

    @pytest.mark.asyncio
    async def test_generate_template_preview_with_custom_template(
        self, test_client: AsyncClient
    ) -> None:
        """Test that a user-provided question_text_template is echoed back."""
        request_data: dict[str, Any] = {
            "code": "def example(n):\\n    return n * 2",
            "execution_spec": {"entry_function": "example"},
            "question_spec": {
                "target": [
                    {
                        "type": "function",
                        "id": [0],
                        "name": "example",
                        "line_number": 1,
                        "modifier": "return_value",
                    }
                ],
                "output_type": "first",
                "question_type": "mcq",
            },
            "generation_options": {"num_distractors": 4},
            "question_text_template": "Custom template: n = {n}",
            "text_template_type": "basic",
        }

        data = await _submit_and_poll(
            test_client, "/question-generation/generate-template", request_data
        )

        assert data["status"] == "completed"
        result = data["result"]
        assert result["question_text_template"] == "Custom template: n = {n}"
        assert result["text_template_type"] == "basic"

    @pytest.mark.asyncio
    async def test_generate_template_preview_invalid_code_encoding(
        self, test_client: AsyncClient
    ) -> None:
        """Test that invalid code encoding causes the job to fail."""
        request_data: dict[str, Any] = {
            "code": "\\x",  # Invalid escape sequence
            "execution_spec": {"entry_function": "example"},
            "question_spec": {
                "target": [
                    {
                        "type": "function",
                        "id": [0],
                        "name": "example",
                        "modifier": "return_value",
                    }
                ],
                "output_type": "first",
                "question_type": "mcq",
            },
            "generation_options": {"num_distractors": 4},
        }

        data = await _submit_and_poll(
            test_client, "/question-generation/generate-template", request_data
        )

        assert data["status"] == "failed"
        assert data["error"] is not None

    @pytest.mark.asyncio
    async def test_generate_template_preview_preserves_all_config(
        self, test_client: AsyncClient
    ) -> None:
        """Test that response preserves all input configuration."""
        request_data: dict[str, Any] = {
            "code": "def example(x, y):\\n    return x + y",
            "execution_spec": {"entry_function": "example"},
            "question_spec": {
                "target": [
                    {
                        "type": "function",
                        "id": [0],
                        "name": "example",
                        "line_number": 1,
                        "modifier": "arguments",
                    }
                ],
                "output_type": "list",
                "question_type": "mrq",
            },
            "generation_options": {"num_distractors": 3},
        }

        data = await _submit_and_poll(
            test_client, "/question-generation/generate-template", request_data
        )

        assert data["status"] == "completed"
        result = data["result"]

        # Verify all config is preserved
        assert result["entry_function"] == "example"
        assert result["output_type"] == "list"
        assert result["question_type"] == "mrq"
        assert result["target_elements"][0]["modifier"] == "arguments"
        assert result["num_distractors"] == 3

    @pytest.mark.asyncio
    async def test_generate_template_preview_with_input_data(
        self, test_client: AsyncClient
    ) -> None:
        """Test preview question is generated with real values when input_data is provided."""
        request_data: dict[str, Any] = {
            "code": "def example(n):\\n    return n * 2",
            "execution_spec": {"entry_function": "example", "input_data": {"n": 5}},
            "question_spec": {
                "target": [
                    {
                        "type": "function",
                        "id": [0],
                        "name": "example",
                        "line_number": 1,
                        "modifier": "return_value",
                    }
                ],
                "output_type": "first",
                "question_type": "mcq",
            },
            "generation_options": {"num_distractors": 4},
        }

        data = await _submit_and_poll(
            test_client, "/question-generation/generate-template", request_data
        )

        assert data["status"] == "completed"
        preview = data["result"]["preview_question"]
        assert preview["answer"] == "Option A"
        assert "Option A" in preview["options"]
