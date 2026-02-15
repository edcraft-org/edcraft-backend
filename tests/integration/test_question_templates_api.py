"""Integration tests for Question Templates API endpoints."""

from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from edcraft_backend.models.user import User
from tests.factories import (
    create_test_assessment_template,
    create_test_question_template,
    create_test_question_template_bank,
    create_test_user,
    link_question_template_to_assessment_template,
    link_question_template_to_question_template_bank,
)


@pytest.mark.integration
@pytest.mark.question_templates
class TestListQuestionTemplates:
    """Tests for GET /question-templates endpoint."""

    @pytest.mark.asyncio
    async def test_list_question_templates_success(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test listing all question templates for a user."""
        template1 = await create_test_question_template(
            db_session, user, question_type="mcq"
        )
        template2 = await create_test_question_template(
            db_session, user, question_type="mrq"
        )
        await db_session.commit()

        response = await test_client.get("/question-templates")

        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 2
        template_ids = [t["id"] for t in data]
        assert str(template1.id) in template_ids
        assert str(template2.id) in template_ids

    @pytest.mark.asyncio
    async def test_list_question_templates_excludes_soft_deleted(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test that soft-deleted templates are not in list."""
        active_template = await create_test_question_template(
            db_session, user, question_text="Active template"
        )
        deleted_template = await create_test_question_template(
            db_session, user, question_text="Deleted template"
        )
        await db_session.commit()

        # Soft delete one template
        await test_client.delete(f"/question-templates/{deleted_template.id}")

        # List templates
        response = await test_client.get("/question-templates")

        assert response.status_code == 200
        data = response.json()
        template_ids = [t["id"] for t in data]
        assert str(active_template.id) in template_ids
        assert str(deleted_template.id) not in template_ids


@pytest.mark.integration
@pytest.mark.question_templates
class TestGetQuestionTemplate:
    """Tests for GET /question-templates/{template_id} endpoint."""

    @pytest.mark.asyncio
    async def test_get_question_template_success(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test getting a question template successfully."""
        template = await create_test_question_template(
            db_session,
            user,
            question_type="mcq",
            question_text="Test question?",
        )
        await db_session.commit()

        response = await test_client.get(f"/question-templates/{template.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(template.id)
        assert data["question_type"] == "mcq"
        assert data["question_text"] == "Test question?"
        assert "description" in data
        assert "entry_function_params" in data
        assert "parameters" in data["entry_function_params"]
        assert "has_var_args" in data["entry_function_params"]
        assert "has_var_kwargs" in data["entry_function_params"]

    @pytest.mark.asyncio
    async def test_get_question_template_with_description(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test getting a question template with description."""
        template = await create_test_question_template(
            db_session,
            user,
            question_type="mcq",
            question_text="Test question?",
            description="Test description for template",
        )
        await db_session.commit()

        response = await test_client.get(f"/question-templates/{template.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["description"] == "Test description for template"

    @pytest.mark.asyncio
    async def test_get_question_template_with_entry_function_params(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test that entry_function_params are correctly parsed from valid code."""
        template = await create_test_question_template(
            db_session,
            user,
            question_type="mcq",
            question_text="What does the function return?",
            code="def calculate(x: int, y: int = 10, *args, z: str = 'test', **kwargs) -> int:\n    return x + y",  # noqa: E501
            entry_function="calculate",
            num_distractors=3,
            output_type="first",
            target_elements=[
                {
                    "element_type": "function",
                    "id_list": [0],
                    "name": "calculate",
                    "line_number": 1,
                    "modifier": "return_value",
                }
            ],
        )
        await db_session.commit()

        response = await test_client.get(f"/question-templates/{template.id}")

        assert response.status_code == 200
        data = response.json()
        assert "entry_function_params" in data
        params = data["entry_function_params"]

        assert params["parameters"] == ["x", "y", "z"]
        assert params["has_var_args"] is True
        assert params["has_var_kwargs"] is True

    @pytest.mark.asyncio
    async def test_get_question_template_not_found(
        self, test_client: AsyncClient, user: User
    ) -> None:
        """Test getting non-existent template returns 404."""
        import uuid

        non_existent_id = uuid.uuid4()
        response = await test_client.get(f"/question-templates/{non_existent_id}")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_get_question_template_soft_deleted_returns_404(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test getting soft-deleted template returns 404."""
        template = await create_test_question_template(db_session, user)
        await db_session.commit()

        # Soft delete the template
        await test_client.delete(f"/question-templates/{template.id}")

        # Try to get the soft-deleted template
        response = await test_client.get(f"/question-templates/{template.id}")

        assert response.status_code == 404


@pytest.mark.integration
@pytest.mark.question_templates
class TestUpdateQuestionTemplate:
    """Tests for PATCH /question-templates/{template_id} endpoint."""

    @pytest.mark.asyncio
    async def test_update_question_template_question_text(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test updating question template text successfully."""
        template = await create_test_question_template(
            db_session, user, question_text="Old text"
        )
        await db_session.commit()

        update_data = {"question_text": "New text"}
        response = await test_client.patch(
            f"/question-templates/{template.id}", json=update_data
        )

        assert response.status_code == 200
        data = response.json()
        assert data["question_text"] == "New text"

    @pytest.mark.asyncio
    async def test_update_question_template_description(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test updating question template description successfully."""
        template = await create_test_question_template(
            db_session, user, description="Old description"
        )
        await db_session.commit()

        update_data = {"description": "New description"}
        response = await test_client.patch(
            f"/question-templates/{template.id}", json=update_data
        )

        assert response.status_code == 200
        data = response.json()
        assert data["description"] == "New description"

    @pytest.mark.asyncio
    async def test_update_question_template_clear_description(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test clearing description by setting it to None."""
        template = await create_test_question_template(
            db_session, user, description="Has description"
        )
        await db_session.commit()

        update_data = {"description": None}
        response = await test_client.patch(
            f"/question-templates/{template.id}", json=update_data
        )

        assert response.status_code == 200
        data = response.json()
        assert data["description"] is None

    @pytest.mark.asyncio
    async def test_update_question_template_config(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test updating template fields successfully."""
        template = await create_test_question_template(
            db_session,
            user,
            code="def multiply(x, y):\n    return x * y",
            entry_function="multiply",
            num_distractors=3,
            output_type="first",
            target_elements=[
                {
                    "element_type": "function",
                    "id_list": [0],
                    "name": "multiply",
                    "line_number": 1,
                    "modifier": "return_value",
                }
            ],
        )
        await db_session.commit()

        update_data: dict[str, Any] = {
            "num_distractors": 4,
            "target_elements": [
                {
                    "element_type": "function",
                    "id_list": [0],
                    "name": "multiply",
                    "line_number": 1,
                    "modifier": "return_value",
                }
            ],
        }
        response = await test_client.patch(
            f"/question-templates/{template.id}", json=update_data
        )

        assert response.status_code == 200
        data = response.json()
        assert data["num_distractors"] == 4

    @pytest.mark.asyncio
    async def test_update_question_template_not_found(
        self, test_client: AsyncClient, user: User
    ) -> None:
        """Test updating non-existent template returns 404."""
        import uuid

        non_existent_id = uuid.uuid4()
        update_data = {"question_text": "New text"}
        response = await test_client.patch(
            f"/question-templates/{non_existent_id}", json=update_data
        )

        assert response.status_code == 404


@pytest.mark.integration
@pytest.mark.question_templates
class TestSoftDeleteQuestionTemplate:
    """Tests for DELETE /question-templates/{template_id} endpoint."""

    @pytest.mark.asyncio
    async def test_soft_delete_question_template_success(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test soft deleting question template successfully."""
        template = await create_test_question_template(db_session, user)
        await db_session.commit()

        response = await test_client.delete(f"/question-templates/{template.id}")

        assert response.status_code == 204

        # Verify template has deleted_at timestamp
        await db_session.refresh(template)
        assert template.deleted_at is not None

    @pytest.mark.asyncio
    async def test_soft_delete_question_template_not_in_list(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test soft-deleted template not in list results."""
        template = await create_test_question_template(db_session, user)
        await db_session.commit()

        # Soft delete template
        await test_client.delete(f"/question-templates/{template.id}")

        # List templates
        response = await test_client.get("/question-templates")

        assert response.status_code == 200
        data = response.json()
        template_ids = [t["id"] for t in data]
        assert str(template.id) not in template_ids

    @pytest.mark.asyncio
    async def test_soft_delete_question_template_not_found(
        self, test_client: AsyncClient, user: User
    ) -> None:
        """Test soft deleting non-existent template returns 404."""
        import uuid

        non_existent_id = uuid.uuid4()
        response = await test_client.delete(f"/question-templates/{non_existent_id}")

        assert response.status_code == 404


@pytest.mark.integration
@pytest.mark.question_templates
class TestGetQuestionTemplateUsage:
    """Tests for GET /question-templates/{id}/usage endpoint."""

    @pytest.mark.asyncio
    async def test_get_question_template_usage_success(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test getting usage information for a question template."""
        question_template = await create_test_question_template(db_session, user)
        assessment_template1 = await create_test_assessment_template(
            db_session, user, title="Assessment Template 1"
        )
        assessment_template2 = await create_test_assessment_template(
            db_session, user, title="Assessment Template 2"
        )
        question_template_bank1 = await create_test_question_template_bank(
            db_session, user, title="Question Template Bank 1"
        )
        question_template_bank2 = await create_test_question_template_bank(
            db_session, user, title="Question Template Bank 2"
        )
        await db_session.commit()

        # Link question template to both assessment templates
        await link_question_template_to_assessment_template(
            db_session, assessment_template1.id, question_template.id
        )
        await link_question_template_to_assessment_template(
            db_session, assessment_template2.id, question_template.id
        )
        await link_question_template_to_question_template_bank(
            db_session, question_template_bank1.id, question_template.id
        )
        await link_question_template_to_question_template_bank(
            db_session, question_template_bank2.id, question_template.id
        )
        await db_session.commit()

        # Get usage information for question template
        response = await test_client.get(
            f"/question-templates/{question_template.id}/usage",
        )

        assert response.status_code == 200
        data = response.json()

        assert "assessment_templates" in data
        assert "question_template_banks" in data

        assert len(data["assessment_templates"]) == 2
        template_ids = [t["id"] for t in data["assessment_templates"]]
        assert str(assessment_template1.id) in template_ids
        assert str(assessment_template2.id) in template_ids

        assert len(data["question_template_banks"]) == 2
        bank_ids = [b["id"] for b in data["question_template_banks"]]
        assert str(question_template_bank1.id) in bank_ids
        assert str(question_template_bank2.id) in bank_ids

    @pytest.mark.asyncio
    async def test_get_question_template_usage_unauthorized(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test accessing usage information for question template not owned by current user."""
        other_user = await create_test_user(db_session, email="other@test.com")
        question_template = await create_test_question_template(db_session, other_user)
        await db_session.commit()

        response = await test_client.get(
            f"/question-templates/{question_template.id}/usage",
        )

        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_get_question_template_usage_not_found(
        self, test_client: AsyncClient, user: User
    ) -> None:
        """Test getting usage information for non-existent question template."""
        import uuid

        non_existent_id = uuid.uuid4()
        response = await test_client.get(
            f"/question-templates/{non_existent_id}/usage",
        )

        assert response.status_code == 404
