"""Integration tests for Question Generation API endpoints."""

from typing import Any
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.factories import (
    create_assessment_template_with_question_templates,
    create_test_folder,
    create_test_question_template,
    create_test_user,
)


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
        response = await test_client.post("/question-generation/analyse-code", json=code_data)

        assert response.status_code == 200
        data = response.json()
        assert "code_info" in data
        assert "form_elements" in data
        # Verify code_info structure
        assert "code_tree" in data["code_info"]
        assert "functions" in data["code_info"]
        assert "loops" in data["code_info"]
        assert "branches" in data["code_info"]
        assert "variables" in data["code_info"]

    @pytest.mark.asyncio
    async def test_analyse_code_empty_code(self, test_client: AsyncClient) -> None:
        """Test code analysis with empty code."""
        code_data = {"code": ""}
        response = await test_client.post("/question-generation/analyse-code", json=code_data)

        assert response.status_code == 200
        data = response.json()
        # Empty code should still return valid structure
        assert "code_info" in data
        assert "form_elements" in data
        # Verify code_info structure
        assert "code_tree" in data["code_info"]
        assert "functions" in data["code_info"]
        assert "loops" in data["code_info"]
        assert "branches" in data["code_info"]
        assert "variables" in data["code_info"]

    @pytest.mark.asyncio
    async def test_analyse_code_with_invalid_encoding(self, test_client: AsyncClient) -> None:
        """Test that invalid code encoding raises appropriate error."""
        code_data = {
            "code": "\\x",  # Invalid escape sequence
        }

        response = await test_client.post("/question-generation/analyse-code", json=code_data)

        assert response.status_code == 400
        assert "Invalid code format" in response.json()["detail"]


@pytest.mark.integration
@pytest.mark.question_generation
class TestGenerateQuestionFromTemplate:
    """Tests for POST /question-generation/from-template/{template_id} endpoint."""

    @pytest.mark.asyncio
    async def test_generate_question_from_template_success(
        self, test_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test successfully generating a question from a template."""
        # Create user and question template with valid config
        user = await create_test_user(db_session)
        template = await create_test_question_template(
            db_session,
            user,
            question_type="mcq",
            template_config={
                "code": "def example(n):\n    return n * 2",
                "entry_function": "example",
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
            },
        )
        await db_session.commit()

        # Call endpoint with valid input_data
        request_data = {"input_data": {"n": 5}}
        response = await test_client.post(
            f"/question-generation/from-template/{template.id}",
            json=request_data,
        )

        # Assert success
        assert response.status_code == 200
        data = response.json()

        # Verify question structure
        assert "text" in data
        assert "question_type" in data
        assert data["question_type"] == "mcq"
        assert "options" in data
        assert "correct_indices" in data
        assert len(data["options"]) > 0

    @pytest.mark.asyncio
    async def test_generate_question_from_template_not_found(
        self, test_client: AsyncClient
    ) -> None:
        """Test generating question from non-existent template returns 404."""
        non_existent_id = uuid4()
        request_data = {"input_data": {"n": 5}}

        response = await test_client.post(
            f"/question-generation/from-template/{non_existent_id}",
            json=request_data,
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_generate_question_from_template_missing_field(
        self, test_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test template with missing 'code' field raises ValidationError."""
        user = await create_test_user(db_session)
        template = await create_test_question_template(
            db_session,
            user,
            template_config={
                # Missing 'code' field
                "entry_function": "example",
                "question_spec": {"question_type": "mcq"},
                "generation_options": {"num_distractors": 4},
            },
        )
        await db_session.commit()

        request_data = {"input_data": {"n": 5}}
        response = await test_client.post(
            f"/question-generation/from-template/{template.id}",
            json=request_data,
        )

        assert response.status_code == 400
        assert "code" in response.json()["detail"].lower()


@pytest.mark.integration
@pytest.mark.question_generation
class TestGenerateAssessmentFromTemplate:
    """Tests for POST /question-generation/assessment-from-template/{template_id} endpoint."""

    @pytest.mark.asyncio
    async def test_generate_assessment_from_template_success(
        self, test_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test successfully generating an assessment from a template."""
        # Create user and assessment template with 3 question templates
        user = await create_test_user(db_session)
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
        response = await test_client.post(
            f"/question-generation/assessment-from-template/{assessment_template.id}",
            json=request_data,
        )

        # Assert success
        assert response.status_code == 201
        data = response.json()

        # Verify assessment created with correct metadata
        assert data["title"] == "Custom Assessment"
        assert data["description"] == "Custom description"
        assert data["owner_id"] == str(user.id)

        # Verify 3 questions created and linked in correct order
        assert len(data["questions"]) == 3
        for i, question in enumerate(data["questions"]):
            assert question["order"] == i
            assert question["template_id"] == str(question_templates[i].id)

    @pytest.mark.asyncio
    async def test_generate_assessment_from_template_uses_template_defaults(
        self, test_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test assessment uses template defaults when metadata not provided."""
        user = await create_test_user(db_session)
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
        response = await test_client.post(
            f"/question-generation/assessment-from-template/{assessment_template.id}",
            json=request_data,
        )

        assert response.status_code == 201
        data = response.json()

        assert data["title"] == assessment_template.title
        assert data["description"] == assessment_template.description

    @pytest.mark.asyncio
    async def test_generate_assessment_from_template_overrides_defaults(
        self, test_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test custom metadata overrides template defaults."""
        user = await create_test_user(db_session)
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
        response = await test_client.post(
            f"/question-generation/assessment-from-template/{assessment_template.id}",
            json=request_data,
        )

        assert response.status_code == 201
        data = response.json()

        assert data["title"] == "Override Title"
        assert data["description"] == "Override Description"

    @pytest.mark.asyncio
    async def test_generate_assessment_from_template_with_folder(
        self, test_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test assessment is created in the specified folder."""
        user = await create_test_user(db_session)
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
        response = await test_client.post(
            f"/question-generation/assessment-from-template/{assessment_template.id}",
            json=request_data,
        )

        assert response.status_code == 201
        data = response.json()
        assert data["folder_id"] == str(folder.id)

    @pytest.mark.asyncio
    async def test_generate_assessment_from_template_not_found(
        self, test_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test generating assessment from non-existent template returns 404."""
        user = await create_test_user(db_session)
        await db_session.commit()

        non_existent_id = uuid4()
        request_data: dict[str, Any] = {
            "assessment_metadata": {"owner_id": str(user.id)},
            "question_inputs": [{"n": 5}],
        }

        response = await test_client.post(
            f"/question-generation/assessment-from-template/{non_existent_id}",
            json=request_data,
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_generate_assessment_from_template_input_count_mismatch(
        self, test_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test input count mismatch raises ValidationError."""
        user = await create_test_user(db_session)
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

        response = await test_client.post(
            f"/question-generation/assessment-from-template/{assessment_template.id}",
            json=request_data,
        )

        assert response.status_code == 400
        error_detail = response.json()["detail"]
        assert "expected 3" in error_detail.lower()
        assert "got 2" in error_detail.lower()

    @pytest.mark.asyncio
    async def test_generate_assessment_from_template_empty_template(
        self, test_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test assessment template with no question templates creates empty assessment."""
        from edcraft_backend.models.assessment_template import AssessmentTemplate
        from tests.factories import get_user_root_folder

        user = await create_test_user(db_session)
        root_folder = await get_user_root_folder(db_session, user)
        template = AssessmentTemplate(
            owner_id=user.id,
            folder_id=root_folder.id,
            title="Empty Template",
            description="No questions",
        )
        db_session.add(template)
        await db_session.commit()

        request_data: dict[str, Any] = {
            "assessment_metadata": {"owner_id": str(user.id)},
            "question_inputs": [],  # Empty array
        }

        response = await test_client.post(
            f"/question-generation/assessment-from-template/{template.id}",
            json=request_data,
        )

        assert response.status_code == 201
        data = response.json()
        assert len(data["questions"]) == 0

    @pytest.mark.asyncio
    async def test_generate_assessment_from_template_preserves_question_order(
        self, test_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test questions are created in the same order as templates."""
        user = await create_test_user(db_session)
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

        response = await test_client.post(
            f"/question-generation/assessment-from-template/{assessment_template.id}",
            json=request_data,
        )

        assert response.status_code == 201
        data = response.json()

        assert len(data["questions"]) == 5
        for i in range(5):
            assert data["questions"][i]["order"] == i
            assert data["questions"][i]["template_id"] == str(question_templates[i].id)

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
            "entry_function": "example",
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

        response = await test_client.post(
            "/question-generation/generate-template", json=request_data
        )

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "question_text" in data
        assert "question_type" in data
        assert "template_config" in data
        assert "preview_question" in data

        # Verify question_type
        assert data["question_type"] == "mcq"

        # Verify question_text does NOT contain "Given input:"
        assert "Given input:" not in data["question_text"]

        # Verify template_config structure
        config = data["template_config"]
        assert config["code"] == "def example(n):\n    return n * 2"
        assert config["entry_function"] == "example"
        assert "question_spec" in config
        assert "generation_options" in config
        assert config["generation_options"]["num_distractors"] == 4

        # Verify preview_question structure
        preview = data["preview_question"]
        assert preview["text"] == data["question_text"]
        assert preview["question_type"] == "mcq"
        assert preview["answer"] == "<placeholder_answer>"
        assert preview["options"] is not None
        assert len(preview["options"]) == 5  # 4 distractors + 1 correct
        assert preview["correct_indices"] == [0]

        # Verify placeholder options format
        for i, option in enumerate(preview["options"]):
            assert option == f"<option_{i+1}>"

    @pytest.mark.asyncio
    async def test_generate_template_preview_invalid_code_encoding(
        self, test_client: AsyncClient
    ) -> None:
        """Test that invalid code encoding raises CodeDecodingError."""
        request_data: dict[str, Any] = {
            "code": "\\x",  # Invalid escape sequence
            "entry_function": "example",
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

        response = await test_client.post(
            "/question-generation/generate-template", json=request_data
        )

        assert response.status_code == 400
        assert "Invalid code format" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_generate_template_preview_preserves_all_config(
        self, test_client: AsyncClient
    ) -> None:
        """Test that template_config preserves all input configuration."""
        request_data: dict[str, Any] = {
            "code": "def example(x, y):\\n    return x + y",
            "entry_function": "example",
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

        response = await test_client.post(
            "/question-generation/generate-template", json=request_data
        )

        assert response.status_code == 200
        data = response.json()

        # Verify all config is preserved
        config = data["template_config"]
        assert config["entry_function"] == "example"
        assert config["question_spec"]["output_type"] == "list"
        assert config["question_spec"]["question_type"] == "mrq"
        assert config["question_spec"]["target"][0]["modifier"] == "arguments"
        assert config["generation_options"]["num_distractors"] == 3
