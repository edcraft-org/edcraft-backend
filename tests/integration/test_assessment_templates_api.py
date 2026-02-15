"""Integration tests for Assessment Templates API endpoints."""

from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from edcraft_backend.models.question_template import QuestionTemplate
from edcraft_backend.models.user import User
from tests.factories import (
    create_test_assessment_template,
    create_test_folder,
    create_test_question_template,
    create_test_question_template_bank,
    link_question_template_to_question_template_bank,
)


@pytest.mark.integration
@pytest.mark.assessment_templates
class TestCreateAssessmentTemplate:
    """Tests for POST /assessment-templates endpoint."""

    @pytest.mark.asyncio
    async def test_create_assessment_template_with_folder(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test creating assessment template linked to folder."""
        folder = await create_test_folder(db_session, user)
        await db_session.commit()

        template_data = {
            "folder_id": str(folder.id),
            "title": "Template in Folder",
            "description": "Test description",
        }
        response = await test_client.post("/assessment-templates", json=template_data)

        assert response.status_code == 201
        data = response.json()
        assert data["folder_id"] == str(folder.id)

    @pytest.mark.asyncio
    async def test_create_assessment_template_nonexistent_folder(
        self, test_client: AsyncClient, user: User
    ) -> None:
        """Test creating assessment template with non-existent folder returns 404."""
        import uuid

        non_existent_folder_id = uuid.uuid4()
        template_data = {
            "folder_id": str(non_existent_folder_id),
            "title": "Test Template",
        }
        response = await test_client.post("/assessment-templates", json=template_data)

        assert response.status_code == 404


@pytest.mark.integration
@pytest.mark.assessment_templates
class TestListAssessmentTemplates:
    """Tests for GET /assessment-templates endpoint."""

    @pytest.mark.asyncio
    async def test_list_assessment_templates_success(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test listing all assessment templates for a user."""
        template1 = await create_test_assessment_template(
            db_session, user, title="Template 1"
        )
        template2 = await create_test_assessment_template(
            db_session, user, title="Template 2"
        )
        await db_session.commit()

        response = await test_client.get("/assessment-templates")

        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 2
        template_ids = [t["id"] for t in data]
        assert str(template1.id) in template_ids
        assert str(template2.id) in template_ids

    @pytest.mark.asyncio
    async def test_list_assessment_templates_filter_by_folder(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test filtering assessment templates by folder."""
        folder1 = await create_test_folder(db_session, user, name="Folder 1")
        folder2 = await create_test_folder(db_session, user, name="Folder 2")
        template_in_folder1 = await create_test_assessment_template(
            db_session, user, folder=folder1
        )
        await create_test_assessment_template(db_session, user, folder=folder2)
        await db_session.commit()

        response = await test_client.get(
            "/assessment-templates",
            params={"folder_id": str(folder1.id)},
        )

        assert response.status_code == 200
        data = response.json()
        assert all(t["folder_id"] == str(folder1.id) for t in data)
        assert str(template_in_folder1.id) in [t["id"] for t in data]

    @pytest.mark.asyncio
    async def test_list_assessment_templates_excludes_soft_deleted(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test that soft-deleted assessment templates are not in list."""
        active_template = await create_test_assessment_template(
            db_session, user, title="Active"
        )
        deleted_template = await create_test_assessment_template(
            db_session, user, title="Deleted"
        )
        await db_session.commit()

        # Soft delete one template
        await test_client.delete(f"/assessment-templates/{deleted_template.id}")

        # List templates
        response = await test_client.get("/assessment-templates")

        assert response.status_code == 200
        data = response.json()
        template_ids = [t["id"] for t in data]
        assert str(active_template.id) in template_ids
        assert str(deleted_template.id) not in template_ids


@pytest.mark.integration
@pytest.mark.assessment_templates
class TestGetAssessmentTemplate:
    """Tests for GET /assessment-templates/{template_id} endpoint."""

    @pytest.mark.asyncio
    async def test_get_assessment_template_success(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test getting an assessment template successfully."""
        template = await create_test_assessment_template(
            db_session, user, title="Test Template"
        )
        await db_session.commit()

        response = await test_client.get(f"/assessment-templates/{template.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(template.id)
        assert data["title"] == "Test Template"
        assert "question_templates" in data
        assert data["question_templates"] == []

    @pytest.mark.asyncio
    async def test_get_assessment_template_with_question_templates_in_order(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test getting assessment template includes question templates in correct order."""
        template = await create_test_assessment_template(db_session, user)
        qt1 = await create_test_question_template(
            db_session, user, question_text="QT1?"
        )
        qt2 = await create_test_question_template(
            db_session, user, question_text="QT2?"
        )
        qt3 = await create_test_question_template(
            db_session, user, question_text="QT3?"
        )
        await db_session.commit()

        # Link question templates in specific order
        await test_client.post(
            f"/assessment-templates/{template.id}/question-templates/link",
            json={"question_template_id": str(qt1.id)},
        )
        await test_client.post(
            f"/assessment-templates/{template.id}/question-templates/link",
            json={"question_template_id": str(qt2.id)},
        )
        await test_client.post(
            f"/assessment-templates/{template.id}/question-templates/link",
            json={"question_template_id": str(qt3.id)},
        )

        response = await test_client.get(f"/assessment-templates/{template.id}")

        assert response.status_code == 200
        data = response.json()
        assert len(data["question_templates"]) == 3
        # Verify order
        assert data["question_templates"][0]["question_text"] == "QT1?"
        assert data["question_templates"][0]["order"] == 0
        assert data["question_templates"][1]["question_text"] == "QT2?"
        assert data["question_templates"][1]["order"] == 1
        assert data["question_templates"][2]["question_text"] == "QT3?"
        assert data["question_templates"][2]["order"] == 2

    @pytest.mark.asyncio
    async def test_get_assessment_template_not_found(
        self, test_client: AsyncClient, user: User
    ) -> None:
        """Test getting non-existent assessment template returns 404."""
        import uuid

        non_existent_id = uuid.uuid4()
        response = await test_client.get(f"/assessment-templates/{non_existent_id}")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_get_assessment_template_soft_deleted_returns_404(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test getting soft-deleted assessment template returns 404."""
        template = await create_test_assessment_template(db_session, user)
        await db_session.commit()

        # Soft delete the template
        await test_client.delete(f"/assessment-templates/{template.id}")

        # Try to get the soft-deleted template
        response = await test_client.get(f"/assessment-templates/{template.id}")

        assert response.status_code == 404


@pytest.mark.integration
@pytest.mark.assessment_templates
class TestUpdateAssessmentTemplate:
    """Tests for PATCH /assessment-templates/{template_id} endpoint."""

    @pytest.mark.asyncio
    async def test_update_assessment_template_title(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test updating assessment template title successfully."""
        template = await create_test_assessment_template(
            db_session, user, title="Old Title"
        )
        await db_session.commit()

        update_data = {"title": "New Title"}
        response = await test_client.patch(
            f"/assessment-templates/{template.id}", json=update_data
        )

        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "New Title"

    @pytest.mark.asyncio
    async def test_update_assessment_template_description(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test updating assessment template description successfully."""
        template = await create_test_assessment_template(
            db_session, user, description="Old description"
        )
        await db_session.commit()

        update_data = {"description": "New description"}
        response = await test_client.patch(
            f"/assessment-templates/{template.id}", json=update_data
        )

        assert response.status_code == 200
        data = response.json()
        assert data["description"] == "New description"

    @pytest.mark.asyncio
    async def test_update_assessment_template_move_to_folder(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test moving assessment template to different folder."""
        folder1 = await create_test_folder(db_session, user, name="Folder 1")
        folder2 = await create_test_folder(db_session, user, name="Folder 2")
        template = await create_test_assessment_template(
            db_session, user, folder=folder1
        )
        await db_session.commit()

        update_data = {"folder_id": str(folder2.id)}
        response = await test_client.patch(
            f"/assessment-templates/{template.id}", json=update_data
        )

        assert response.status_code == 200
        data = response.json()
        assert data["folder_id"] == str(folder2.id)

    @pytest.mark.asyncio
    async def test_update_assessment_template_not_found(
        self, test_client: AsyncClient, user: User
    ) -> None:
        """Test updating non-existent assessment template returns 404."""
        import uuid

        non_existent_id = uuid.uuid4()
        update_data = {"title": "New Title"}
        response = await test_client.patch(
            f"/assessment-templates/{non_existent_id}", json=update_data
        )

        assert response.status_code == 404


@pytest.mark.integration
@pytest.mark.assessment_templates
class TestSoftDeleteAssessmentTemplate:
    """Tests for DELETE /assessment-templates/{template_id} endpoint."""

    @pytest.mark.asyncio
    async def test_soft_delete_assessment_template_success(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test soft deleting assessment template successfully."""
        template = await create_test_assessment_template(db_session, user)
        await db_session.commit()

        response = await test_client.delete(f"/assessment-templates/{template.id}")

        assert response.status_code == 204

        # Verify template has deleted_at timestamp
        await db_session.refresh(template)
        assert template.deleted_at is not None

    @pytest.mark.asyncio
    async def test_soft_delete_assessment_template_not_in_list(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test soft-deleted assessment template not in list results."""
        template = await create_test_assessment_template(db_session, user)
        await db_session.commit()

        # Soft delete template
        await test_client.delete(f"/assessment-templates/{template.id}")

        # List templates
        response = await test_client.get("/assessment-templates")

        assert response.status_code == 200
        data = response.json()
        template_ids = [t["id"] for t in data]
        assert str(template.id) not in template_ids

    @pytest.mark.asyncio
    async def test_soft_delete_assessment_template_not_found(
        self, test_client: AsyncClient, user: User
    ) -> None:
        """Test soft deleting non-existent assessment template returns 404."""
        import uuid

        non_existent_id = uuid.uuid4()
        response = await test_client.delete(f"/assessment-templates/{non_existent_id}")

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_soft_delete_template_cleans_up_orphaned_question_templates(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test that deleting template triggers cleanup of orphaned question templates."""
        from sqlalchemy import select

        from edcraft_backend.models.question_template import QuestionTemplate

        template = await create_test_assessment_template(db_session, user)

        orphaned_qt = await create_test_question_template(
            db_session, user, question_text="Orphaned QT"
        )

        shared_qt = await create_test_question_template(
            db_session, user, question_text="Shared QT"
        )
        other_template = await create_test_assessment_template(
            db_session, user, title="Other Template"
        )
        await db_session.commit()

        await test_client.post(
            f"/assessment-templates/{template.id}/question-templates/link",
            json={"question_template_id": str(orphaned_qt.id)},
        )

        await test_client.post(
            f"/assessment-templates/{template.id}/question-templates/link",
            json={"question_template_id": str(shared_qt.id)},
        )
        await test_client.post(
            f"/assessment-templates/{other_template.id}/question-templates/link",
            json={"question_template_id": str(shared_qt.id)},
        )

        response = await test_client.delete(f"/assessment-templates/{template.id}")
        assert response.status_code == 204

        orphaned_qt_id = orphaned_qt.id
        shared_qt_id = shared_qt.id

        db_session.expire_all()
        orphaned_qt_result = await db_session.execute(
            select(QuestionTemplate).where(QuestionTemplate.id == orphaned_qt_id)
        )
        orphaned_qt_db = orphaned_qt_result.scalar_one_or_none()
        assert orphaned_qt_db is not None
        assert (
            orphaned_qt_db.deleted_at is not None
        ), "Orphaned question template should be soft deleted"

        shared_qt_result = await db_session.execute(
            select(QuestionTemplate).where(QuestionTemplate.id == shared_qt_id)
        )
        shared_qt_db = shared_qt_result.scalar_one_or_none()
        assert shared_qt_db is not None
        assert (
            shared_qt_db.deleted_at is None
        ), "Shared question template should still be active"

    @pytest.mark.asyncio
    async def test_delete_template_preserves_question_template_still_in_use(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test that deleting assessment template doesn't delete question template still used."""
        from sqlalchemy import select


        # Create assessment template and question template bank
        assessment = await create_test_assessment_template(db_session, user)
        question_bank = await create_test_question_template_bank(
            db_session, user, title="Test Question Template Bank"
        )

        # Create a question used in both assessment template and question template bank
        shared_question = await create_test_question_template(
            db_session,
            user,
            question_text="Question in both assessment template and bank",
        )
        await db_session.commit()

        # Link question to both assessment template and question template bank
        await test_client.post(
            f"/assessment-templates/{assessment.id}/question-templates/link",
            json={"question_template_id": str(shared_question.id)},
        )
        await link_question_template_to_question_template_bank(
            db_session, question_bank.id, shared_question.id
        )
        await db_session.commit()

        # Delete the assessment
        response = await test_client.delete(f"/assessment-templates/{assessment.id}")
        assert response.status_code == 204

        # Verify the question is still active (not deleted)
        shared_q_id = shared_question.id
        db_session.expire_all()

        result = await db_session.execute(
            select(QuestionTemplate).where(QuestionTemplate.id == shared_q_id)
        )
        question = result.scalar_one_or_none()
        assert question is not None
        assert (
            question.deleted_at is None
        ), "Question template should remain active when still used in question template bank"


@pytest.mark.integration
@pytest.mark.assessment_templates
class TestInsertQuestionTemplateToAssessmentTemplate:
    """Tests for POST /assessment-templates/{template_id}/question-templates endpoint."""

    @pytest.mark.asyncio
    async def test_insert_question_template_to_assessment_template_success(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test inserting question template to assessment template successfully."""
        template = await create_test_assessment_template(db_session, user)
        await db_session.commit()

        qt_data: dict[str, Any] = {
            "question_template": {
                "question_type": "mcq",
                "question_text": "What is 2+2?",
                "code": "def example():\n    return 2 + 2",
                "entry_function": "example",
                "num_distractors": 4,
                "output_type": "first",
                "target_elements": [
                    {
                        "element_type": "function",
                        "id_list": [0],
                        "name": "example",
                        "line_number": 1,
                        "modifier": "return_value",
                    }
                ],
            },
            "order": 0,
        }
        response = await test_client.post(
            f"/assessment-templates/{template.id}/question-templates", json=qt_data
        )

        assert response.status_code == 201
        data = response.json()
        assert len(data["question_templates"]) == 1
        assert data["question_templates"][0]["question_text"] == "What is 2+2?"
        assert data["question_templates"][0]["question_type"] == "mcq"
        assert data["question_templates"][0]["order"] == 0

    @pytest.mark.asyncio
    async def test_insert_multiple_question_templates_with_order(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test inserting multiple question templates with specific order."""
        template = await create_test_assessment_template(db_session, user)
        await db_session.commit()

        # Insert question templates with specific order
        qt_data_1: dict[str, Any] = {
            "question_template": {
                "question_type": "mcq",
                "question_text": "Question 1?",
                "code": "def example1(n):\n    return n * 2",
                "entry_function": "example1",
                "num_distractors": 4,
                "output_type": "first",
                "target_elements": [
                    {
                        "element_type": "function",
                        "id_list": [0],
                        "name": "example1",
                        "line_number": 1,
                        "modifier": "return_value",
                    }
                ],
            },
            "order": 0,
        }
        await test_client.post(
            f"/assessment-templates/{template.id}/question-templates", json=qt_data_1
        )

        qt_data_2: dict[str, Any] = {
            "question_template": {
                "question_type": "mcq",
                "question_text": "Question 2?",
                "code": "def example2(n):\n    return n * 3",
                "entry_function": "example2",
                "num_distractors": 4,
                "output_type": "first",
                "target_elements": [
                    {
                        "element_type": "function",
                        "id_list": [0],
                        "name": "example2",
                        "line_number": 1,
                        "modifier": "return_value",
                    }
                ],
            },
            "order": 1,
        }
        await test_client.post(
            f"/assessment-templates/{template.id}/question-templates", json=qt_data_2
        )

        qt_data_3: dict[str, Any] = {
            "question_template": {
                "question_type": "mcq",
                "question_text": "Question 3?",
                "code": "def example3(n):\n    return n * 4",
                "entry_function": "example3",
                "num_distractors": 4,
                "output_type": "first",
                "target_elements": [
                    {
                        "element_type": "function",
                        "id_list": [0],
                        "name": "example3",
                        "line_number": 1,
                        "modifier": "return_value",
                    }
                ],
            },
            "order": 2,
        }
        response = await test_client.post(
            f"/assessment-templates/{template.id}/question-templates", json=qt_data_3
        )

        assert response.status_code == 201
        data = response.json()
        assert len(data["question_templates"]) == 3
        assert data["question_templates"][0]["question_text"] == "Question 1?"
        assert data["question_templates"][1]["question_text"] == "Question 2?"
        assert data["question_templates"][2]["question_text"] == "Question 3?"

    @pytest.mark.asyncio
    async def test_insert_question_template_default_order(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test inserting question template with default order (auto-increments)."""
        template = await create_test_assessment_template(db_session, user)
        await db_session.commit()

        qt_data: dict[str, Any] = {
            "question_template": {
                "question_type": "mcq",
                "question_text": "Test question?",
                "code": "def example(n):\n    return n * 2",
                "entry_function": "example",
                "num_distractors": 4,
                "output_type": "first",
                "target_elements": [
                    {
                        "element_type": "function",
                        "id_list": [0],
                        "name": "example",
                        "line_number": 1,
                        "modifier": "return_value",
                    }
                ],
            }
        }
        response = await test_client.post(
            f"/assessment-templates/{template.id}/question-templates", json=qt_data
        )

        assert response.status_code == 201
        data = response.json()
        assert data["question_templates"][0]["order"] == 0

    @pytest.mark.asyncio
    async def test_insert_question_template_to_nonexistent_assessment_template(
        self, test_client: AsyncClient, user: User
    ) -> None:
        """Test inserting question template to non-existent assessment template returns 404."""
        import uuid

        non_existent_template_id = uuid.uuid4()
        qt_data: dict[str, Any] = {
            "question_template": {
                "question_type": "mcq",
                "question_text": "Test question?",
                "code": "def example(n):\n    return n * 2",
                "entry_function": "example",
                "num_distractors": 4,
                "output_type": "first",
                "target_elements": [
                    {
                        "element_type": "function",
                        "id_list": [0],
                        "name": "example",
                        "line_number": 1,
                        "modifier": "return_value",
                    }
                ],
            },
            "order": 0,
        }
        response = await test_client.post(
            f"/assessment-templates/{non_existent_template_id}/question-templates",
            json=qt_data,
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_insert_question_template_with_insert_behavior(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test that inserting question template at existing order shifts other templates down."""
        template = await create_test_assessment_template(db_session, user)
        await db_session.commit()

        qt1_data: dict[str, Any] = {
            "question_template": {
                "question_type": "mcq",
                "question_text": "Question Template 1?",
                "code": "def example1():\n    return 1",
                "entry_function": "example1",
                "num_distractors": 4,
                "output_type": "first",
                "target_elements": [
                    {
                        "element_type": "function",
                        "id_list": [0],
                        "name": "example1",
                        "line_number": 1,
                        "modifier": "return_value",
                    }
                ],
            },
            "order": 0,
        }
        await test_client.post(
            f"/assessment-templates/{template.id}/question-templates", json=qt1_data
        )

        qt2_data: dict[str, Any] = {
            "question_template": {
                "question_type": "mcq",
                "question_text": "Question Template 2?",
                "code": "def example2():\n    return 2",
                "entry_function": "example2",
                "num_distractors": 4,
                "output_type": "first",
                "target_elements": [
                    {
                        "element_type": "function",
                        "id_list": [0],
                        "name": "example2",
                        "line_number": 1,
                        "modifier": "return_value",
                    }
                ],
            },
            "order": 0,
        }
        response = await test_client.post(
            f"/assessment-templates/{template.id}/question-templates", json=qt2_data
        )

        assert response.status_code == 201
        data = response.json()
        templates = data["question_templates"]

        assert len(templates) == 2
        assert templates[0]["question_text"] == "Question Template 2?"
        assert templates[0]["order"] == 0
        assert templates[1]["question_text"] == "Question Template 1?"
        assert templates[1]["order"] == 1


@pytest.mark.integration
@pytest.mark.assessment_templates
class TestLinkQuestionTemplateToAssessmentTemplate:
    """Tests for POST /assessment-templates/{template_id}/question-templates/link endpoint."""

    @pytest.mark.asyncio
    async def test_link_question_template_to_assessment_template_success(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test linking question template to assessment template successfully."""
        template = await create_test_assessment_template(db_session, user)
        qt = await create_test_question_template(db_session, user)
        await db_session.commit()

        qt_data: dict[str, Any] = {"question_template_id": str(qt.id), "order": 0}
        response = await test_client.post(
            f"/assessment-templates/{template.id}/question-templates/link", json=qt_data
        )

        assert response.status_code == 201
        data = response.json()
        assert len(data["question_templates"]) == 1
        assert data["question_templates"][0]["id"] == str(qt.id)
        assert data["question_templates"][0]["order"] == 0

    @pytest.mark.asyncio
    async def test_link_multiple_question_templates_with_order(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test linking multiple question templates with specific order."""
        template = await create_test_assessment_template(db_session, user)
        qt1 = await create_test_question_template(db_session, user)
        qt2 = await create_test_question_template(db_session, user)
        qt3 = await create_test_question_template(db_session, user)
        await db_session.commit()

        # Link question templates with specific order
        await test_client.post(
            f"/assessment-templates/{template.id}/question-templates/link",
            json={"question_template_id": str(qt1.id), "order": 0},
        )
        await test_client.post(
            f"/assessment-templates/{template.id}/question-templates/link",
            json={"question_template_id": str(qt2.id), "order": 1},
        )
        response = await test_client.post(
            f"/assessment-templates/{template.id}/question-templates/link",
            json={"question_template_id": str(qt3.id), "order": 2},
        )

        assert response.status_code == 201
        data = response.json()
        assert len(data["question_templates"]) == 3
        assert data["question_templates"][0]["id"] == str(qt1.id)
        assert data["question_templates"][1]["id"] == str(qt2.id)
        assert data["question_templates"][2]["id"] == str(qt3.id)

    @pytest.mark.asyncio
    async def test_link_question_template_default_order(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test linking question template with default order (auto-increments)."""
        template = await create_test_assessment_template(db_session, user)
        qt = await create_test_question_template(db_session, user)
        await db_session.commit()

        qt_data: dict[str, Any] = {"question_template_id": str(qt.id)}
        response = await test_client.post(
            f"/assessment-templates/{template.id}/question-templates/link", json=qt_data
        )

        assert response.status_code == 201
        data = response.json()
        assert data["question_templates"][0]["order"] == 0

    @pytest.mark.asyncio
    async def test_link_question_template_to_nonexistent_assessment_template(
        self, test_client: AsyncClient, user: User
    ) -> None:
        """Test linking question template to non-existent assessment template returns 404."""
        import uuid

        non_existent_template_id = uuid.uuid4()
        qt_data: dict[str, Any] = {
            "question_template_id": str(uuid.uuid4()),
            "order": 0,
        }
        response = await test_client.post(
            f"/assessment-templates/{non_existent_template_id}/question-templates/link",
            json=qt_data,
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_link_nonexistent_question_template_to_assessment_template(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test linking non-existent question template to assessment template returns 404."""
        import uuid

        template = await create_test_assessment_template(db_session, user)
        await db_session.commit()

        non_existent_qt_id = uuid.uuid4()
        qt_data: dict[str, Any] = {
            "question_template_id": str(non_existent_qt_id),
            "order": 0,
        }
        response = await test_client.post(
            f"/assessment-templates/{template.id}/question-templates/link", json=qt_data
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_link_question_template_with_insert_behavior(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test that linking question template at existing order shifts other templates down."""
        template = await create_test_assessment_template(db_session, user)
        qt1 = await create_test_question_template(
            db_session, user, question_text="QT1?"
        )
        qt2 = await create_test_question_template(
            db_session, user, question_text="QT2?"
        )
        await db_session.commit()

        await test_client.post(
            f"/assessment-templates/{template.id}/question-templates/link",
            json={"question_template_id": str(qt1.id), "order": 0},
        )

        response = await test_client.post(
            f"/assessment-templates/{template.id}/question-templates/link",
            json={"question_template_id": str(qt2.id), "order": 0},
        )

        assert response.status_code == 201
        data = response.json()
        templates = data["question_templates"]

        assert len(templates) == 2
        assert templates[0]["question_text"] == "QT2?"
        assert templates[0]["order"] == 0
        assert templates[1]["question_text"] == "QT1?"
        assert templates[1]["order"] == 1

    @pytest.mark.asyncio
    async def test_link_question_template_insert_in_middle(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test linking question template in middle shifts templates at/after position down."""
        template = await create_test_assessment_template(db_session, user)
        qt1 = await create_test_question_template(
            db_session, user, question_text="QT1?"
        )
        qt2 = await create_test_question_template(
            db_session, user, question_text="QT2?"
        )
        qt3 = await create_test_question_template(
            db_session, user, question_text="QT3?"
        )
        qt4 = await create_test_question_template(
            db_session, user, question_text="QT4?"
        )
        qt_new = await create_test_question_template(
            db_session, user, question_text="QT_NEW?"
        )
        await db_session.commit()

        # Add initial question templates
        for qt in [qt1, qt2, qt3, qt4]:
            await test_client.post(
                f"/assessment-templates/{template.id}/question-templates/link",
                json={"question_template_id": str(qt.id)},
            )

        # Insert at position 2 (between QT2 and QT3)
        response = await test_client.post(
            f"/assessment-templates/{template.id}/question-templates/link",
            json={"question_template_id": str(qt_new.id), "order": 2},
        )

        assert response.status_code == 201
        data = response.json()
        templates = data["question_templates"]

        # Verify order: QT1, QT2, QT_NEW, QT3, QT4
        assert len(templates) == 5
        assert templates[0]["question_text"] == "QT1?"
        assert templates[0]["order"] == 0
        assert templates[1]["question_text"] == "QT2?"
        assert templates[1]["order"] == 1
        assert templates[2]["question_text"] == "QT_NEW?"
        assert templates[2]["order"] == 2
        assert templates[3]["question_text"] == "QT3?"
        assert templates[3]["order"] == 3
        assert templates[4]["question_text"] == "QT4?"
        assert templates[4]["order"] == 4

    @pytest.mark.asyncio
    async def test_link_question_template_with_order_exceeding_count(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test linking with order > count fails with validation error."""
        template = await create_test_assessment_template(db_session, user)
        qt1 = await create_test_question_template(
            db_session, user, question_text="QT1?"
        )
        qt2 = await create_test_question_template(
            db_session, user, question_text="QT2?"
        )
        qt_new = await create_test_question_template(
            db_session, user, question_text="QT_NEW?"
        )
        await db_session.commit()

        # Add two question templates (count=2)
        await test_client.post(
            f"/assessment-templates/{template.id}/question-templates/link",
            json={"question_template_id": str(qt1.id)},
        )
        await test_client.post(
            f"/assessment-templates/{template.id}/question-templates/link",
            json={"question_template_id": str(qt2.id)},
        )

        response = await test_client.post(
            f"/assessment-templates/{template.id}/question-templates/link",
            json={"question_template_id": str(qt_new.id), "order": 10},
        )

        assert response.status_code == 400
        assert "Order must be between 0 and 2" in response.json()["detail"]
        assert "Omit order to append" in response.json()["detail"]


@pytest.mark.integration
@pytest.mark.assessment_templates
class TestRemoveQuestionTemplateFromAssessmentTemplate:
    """Tests for DELETE endpoint to remove question templates from assessment templates."""

    @pytest.mark.asyncio
    async def test_remove_question_template_from_assessment_template_success(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test removing question template from assessment template successfully."""
        template = await create_test_assessment_template(db_session, user)
        qt = await create_test_question_template(db_session, user)
        await db_session.commit()

        # Link question template
        await test_client.post(
            f"/assessment-templates/{template.id}/question-templates/link",
            json={"question_template_id": str(qt.id), "order": 0},
        )

        # Remove question template
        response = await test_client.delete(
            f"/assessment-templates/{template.id}/question-templates/{qt.id}"
        )

        assert response.status_code == 204

        # Verify question template removed
        get_response = await test_client.get(f"/assessment-templates/{template.id}")
        assert len(get_response.json()["question_templates"]) == 0

    @pytest.mark.asyncio
    async def test_remove_question_template_preserves_other_question_templates(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test removing one question template preserves other question templates."""
        template = await create_test_assessment_template(db_session, user)
        qt1 = await create_test_question_template(db_session, user)
        qt2 = await create_test_question_template(db_session, user)
        await db_session.commit()

        # Link both question templates
        await test_client.post(
            f"/assessment-templates/{template.id}/question-templates/link",
            json={"question_template_id": str(qt1.id), "order": 0},
        )
        await test_client.post(
            f"/assessment-templates/{template.id}/question-templates/link",
            json={"question_template_id": str(qt2.id), "order": 1},
        )

        # Remove first question template
        await test_client.delete(
            f"/assessment-templates/{template.id}/question-templates/{qt1.id}"
        )

        # Verify only second question template remains
        response = await test_client.get(f"/assessment-templates/{template.id}")
        data = response.json()
        assert len(data["question_templates"]) == 1
        assert data["question_templates"][0]["id"] == str(qt2.id)

    @pytest.mark.asyncio
    async def test_remove_question_template_from_nonexistent_assessment_template(
        self, test_client: AsyncClient, user: User
    ) -> None:
        """Test removing question template from non-existent assessment template returns 404."""
        import uuid

        non_existent_template_id = uuid.uuid4()
        qt_id = uuid.uuid4()
        response = await test_client.delete(
            f"/assessment-templates/{non_existent_template_id}/question-templates/{qt_id}"
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_remove_nonexistent_question_template_from_assessment_template(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test removing non-existent question template from assessment template returns 404."""
        import uuid

        template = await create_test_assessment_template(db_session, user)
        await db_session.commit()

        non_existent_qt_id = uuid.uuid4()
        response = await test_client.delete(
            f"/assessment-templates/{template.id}/question-templates/{non_existent_qt_id}"
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_remove_question_template_normalizes_orders(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test that removing a question template normalizes remaining orders."""
        template = await create_test_assessment_template(db_session, user)
        qt1 = await create_test_question_template(
            db_session, user, question_text="QT1?"
        )
        qt2 = await create_test_question_template(
            db_session, user, question_text="QT2?"
        )
        qt3 = await create_test_question_template(
            db_session, user, question_text="QT3?"
        )
        await db_session.commit()

        await test_client.post(
            f"/assessment-templates/{template.id}/question-templates/link",
            json={"question_template_id": str(qt1.id), "order": 0},
        )
        await test_client.post(
            f"/assessment-templates/{template.id}/question-templates/link",
            json={"question_template_id": str(qt2.id), "order": 1},
        )
        await test_client.post(
            f"/assessment-templates/{template.id}/question-templates/link",
            json={"question_template_id": str(qt3.id), "order": 2},
        )

        await test_client.delete(
            f"/assessment-templates/{template.id}/question-templates/{qt2.id}"
        )

        response = await test_client.get(f"/assessment-templates/{template.id}")
        data = response.json()

        assert len(data["question_templates"]) == 2
        assert data["question_templates"][0]["question_text"] == "QT1?"
        assert data["question_templates"][0]["order"] == 0
        assert data["question_templates"][1]["question_text"] == "QT3?"
        assert data["question_templates"][1]["order"] == 1

    @pytest.mark.asyncio
    async def test_remove_question_template_cleans_up_orphaned_template(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test that removing question template triggers cleanup if it becomes orphaned."""
        from sqlalchemy import select

        from edcraft_backend.models.question_template import QuestionTemplate

        template = await create_test_assessment_template(db_session, user)

        orphaned_qt = await create_test_question_template(
            db_session, user, question_text="Will be orphaned"
        )

        shared_qt = await create_test_question_template(
            db_session, user, question_text="Shared"
        )
        other_template = await create_test_assessment_template(
            db_session, user, title="Other Template"
        )
        await db_session.commit()

        await test_client.post(
            f"/assessment-templates/{template.id}/question-templates/link",
            json={"question_template_id": str(orphaned_qt.id)},
        )
        await test_client.post(
            f"/assessment-templates/{template.id}/question-templates/link",
            json={"question_template_id": str(shared_qt.id)},
        )

        await test_client.post(
            f"/assessment-templates/{other_template.id}/question-templates/link",
            json={"question_template_id": str(shared_qt.id)},
        )

        response = await test_client.delete(
            f"/assessment-templates/{template.id}/question-templates/{orphaned_qt.id}"
        )
        assert response.status_code == 204

        template_id = template.id
        orphaned_qt_id = orphaned_qt.id
        shared_qt_id = shared_qt.id

        db_session.expire_all()
        orphaned_qt_result = await db_session.execute(
            select(QuestionTemplate).where(QuestionTemplate.id == orphaned_qt_id)
        )
        orphaned_qt_db = orphaned_qt_result.scalar_one_or_none()
        assert orphaned_qt_db is not None
        assert (
            orphaned_qt_db.deleted_at is not None
        ), "Question template should be soft deleted when orphaned"

        await test_client.delete(
            f"/assessment-templates/{template_id}/question-templates/{shared_qt_id}"
        )

        db_session.expire_all()
        shared_qt_result = await db_session.execute(
            select(QuestionTemplate).where(QuestionTemplate.id == shared_qt_id)
        )
        shared_qt_db = shared_qt_result.scalar_one_or_none()
        assert shared_qt_db is not None
        assert (
            shared_qt_db.deleted_at is None
        ), "Shared question template should remain active while still in use"


@pytest.mark.integration
@pytest.mark.assessment_templates
class TestReorderQuestionTemplates:
    """Tests for PATCH /assessment-templates/{template_id}/question-templates/reorder endpoint."""

    @pytest.mark.asyncio
    async def test_reorder_question_templates_success(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test reordering question templates successfully."""
        template = await create_test_assessment_template(db_session, user)
        qt1 = await create_test_question_template(
            db_session, user, question_text="QT1?"
        )
        qt2 = await create_test_question_template(
            db_session, user, question_text="QT2?"
        )
        qt3 = await create_test_question_template(
            db_session, user, question_text="QT3?"
        )
        await db_session.commit()

        # Link question templates in initial order
        await test_client.post(
            f"/assessment-templates/{template.id}/question-templates/link",
            json={"question_template_id": str(qt1.id), "order": 0},
        )
        await test_client.post(
            f"/assessment-templates/{template.id}/question-templates/link",
            json={"question_template_id": str(qt2.id), "order": 1},
        )
        await test_client.post(
            f"/assessment-templates/{template.id}/question-templates/link",
            json={"question_template_id": str(qt3.id), "order": 2},
        )

        # Reorder: reverse the order
        reorder_data: dict[str, Any] = {
            "question_template_orders": [
                {"question_template_id": str(qt3.id), "order": 0},
                {"question_template_id": str(qt2.id), "order": 1},
                {"question_template_id": str(qt1.id), "order": 2},
            ]
        }
        response = await test_client.patch(
            f"/assessment-templates/{template.id}/question-templates/reorder",
            json=reorder_data,
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["question_templates"]) == 3
        assert data["question_templates"][0]["question_text"] == "QT3?"
        assert data["question_templates"][1]["question_text"] == "QT2?"
        assert data["question_templates"][2]["question_text"] == "QT1?"

    @pytest.mark.asyncio
    async def test_reorder_question_templates_requires_all_questions(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test reordering only some question templates (partial update)."""
        template = await create_test_assessment_template(db_session, user)
        qt1 = await create_test_question_template(db_session, user)
        qt2 = await create_test_question_template(db_session, user)
        qt3 = await create_test_question_template(db_session, user)
        await db_session.commit()

        # Link question templates
        await test_client.post(
            f"/assessment-templates/{template.id}/question-templates/link",
            json={"question_template_id": str(qt1.id), "order": 0},
        )
        await test_client.post(
            f"/assessment-templates/{template.id}/question-templates/link",
            json={"question_template_id": str(qt2.id), "order": 1},
        )
        await test_client.post(
            f"/assessment-templates/{template.id}/question-templates/link",
            json={"question_template_id": str(qt3.id), "order": 2},
        )

        # Reorder: only swap first two
        reorder_data: dict[str, Any] = {
            "question_template_orders": [
                {"question_template_id": str(qt2.id), "order": 0},
                {"question_template_id": str(qt1.id), "order": 1},
            ]
        }
        response = await test_client.patch(
            f"/assessment-templates/{template.id}/question-templates/reorder",
            json=reorder_data,
        )

        assert response.status_code == 400
        assert (
            "must include all question templates" in response.json()["detail"].lower()
        )

    @pytest.mark.asyncio
    async def test_reorder_question_templates_nonexistent_assessment_template(
        self, test_client: AsyncClient, user: User
    ) -> None:
        """Test reordering question templates in non-existent assessment template returns 404."""
        import uuid

        non_existent_id = uuid.uuid4()
        reorder_data: dict[str, Any] = {
            "question_template_orders": [
                {"question_template_id": str(uuid.uuid4()), "order": 0}
            ]
        }
        response = await test_client.patch(
            f"/assessment-templates/{non_existent_id}/question-templates/reorder",
            json=reorder_data,
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_reorder_normalizes_to_consecutive_integers(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test that reorder normalizes orders to 0, 1, 2, 3..."""
        template = await create_test_assessment_template(db_session, user)
        qt1 = await create_test_question_template(
            db_session, user, question_text="QT1?"
        )
        qt2 = await create_test_question_template(
            db_session, user, question_text="QT2?"
        )
        qt3 = await create_test_question_template(
            db_session, user, question_text="QT3?"
        )
        await db_session.commit()

        # Add question templates
        await test_client.post(
            f"/assessment-templates/{template.id}/question-templates/link",
            json={"question_template_id": str(qt1.id)},
        )
        await test_client.post(
            f"/assessment-templates/{template.id}/question-templates/link",
            json={"question_template_id": str(qt2.id)},
        )
        await test_client.post(
            f"/assessment-templates/{template.id}/question-templates/link",
            json={"question_template_id": str(qt3.id)},
        )

        # Reorder with gaps (order: 5, 10, 100)
        reorder_data: dict[str, Any] = {
            "question_template_orders": [
                {"question_template_id": str(qt1.id), "order": 100},
                {"question_template_id": str(qt2.id), "order": 5},
                {"question_template_id": str(qt3.id), "order": 10},
            ]
        }
        response = await test_client.patch(
            f"/assessment-templates/{template.id}/question-templates/reorder",
            json=reorder_data,
        )

        assert response.status_code == 200
        data = response.json()

        assert data["question_templates"][0]["question_text"] == "QT2?"
        assert data["question_templates"][0]["order"] == 0
        assert data["question_templates"][1]["question_text"] == "QT3?"
        assert data["question_templates"][1]["order"] == 1
        assert data["question_templates"][2]["question_text"] == "QT1?"
        assert data["question_templates"][2]["order"] == 2
