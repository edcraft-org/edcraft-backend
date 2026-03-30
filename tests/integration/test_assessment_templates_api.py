"""Integration tests for Assessment Templates API endpoints."""

from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from edcraft_backend.models.enums import CollaboratorRole, ResourceType
from edcraft_backend.models.user import User
from tests.factories import (
    create_and_login_user,
    create_collaborator,
    create_test_assessment_template,
    create_test_folder,
    create_test_question_template,
    create_test_user,
    link_question_template_to_assessment_template,
)

MINIMAL_CODE_INFO: dict[str, Any] = {
    "code_tree": {
        "id": 0,
        "type": "function",
        "variables": [],
        "function_indices": [],
        "loop_indices": [],
        "branch_indices": [],
        "children": [],
    },
    "functions": [],
    "loops": [],
    "branches": [],
    "variables": [],
}


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

    @pytest.mark.asyncio
    async def test_collab_filter_owned_returns_only_owned(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """collab_filter=owned returns only templates owned by user."""
        owned = await create_test_assessment_template(db_session, user)
        other_owner = await create_test_user(
            db_session, email="other_owner_at@test.com"
        )
        shared = await create_test_assessment_template(db_session, other_owner)
        await db_session.commit()

        await create_collaborator(
            db_session,
            ResourceType.ASSESSMENT_TEMPLATE,
            shared.id,
            user,
            CollaboratorRole.EDITOR,
        )
        await db_session.commit()

        response = await test_client.get(
            "/assessment-templates", params={"collab_filter": "owned"}
        )

        assert response.status_code == 200
        ids = [t["id"] for t in response.json()]
        assert str(owned.id) in ids
        assert str(shared.id) not in ids

    @pytest.mark.asyncio
    async def test_collab_filter_shared_returns_only_shared(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """collab_filter=shared returns only templates where user is non-owner collaborator."""
        owned = await create_test_assessment_template(db_session, user)
        other_owner = await create_test_user(
            db_session, email="other_owner_shared_at@test.com"
        )
        shared = await create_test_assessment_template(db_session, other_owner)
        await db_session.commit()

        await create_collaborator(
            db_session,
            ResourceType.ASSESSMENT_TEMPLATE,
            shared.id,
            user,
            CollaboratorRole.VIEWER,
        )
        await db_session.commit()

        response = await test_client.get(
            "/assessment-templates", params={"collab_filter": "shared"}
        )

        assert response.status_code == 200
        ids = [t["id"] for t in response.json()]
        assert str(shared.id) in ids
        assert str(owned.id) not in ids

    @pytest.mark.asyncio
    async def test_collab_filter_all_returns_both(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """collab_filter=all (default) returns both owned and shared templates."""
        owned = await create_test_assessment_template(db_session, user)
        other_owner = await create_test_user(
            db_session, email="other_owner_all_at@test.com"
        )
        shared = await create_test_assessment_template(db_session, other_owner)
        await db_session.commit()

        await create_collaborator(
            db_session,
            ResourceType.ASSESSMENT_TEMPLATE,
            shared.id,
            user,
            CollaboratorRole.VIEWER,
        )
        await db_session.commit()

        response = await test_client.get("/assessment-templates")

        assert response.status_code == 200
        ids = [t["id"] for t in response.json()]
        assert str(owned.id) in ids
        assert str(shared.id) in ids


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
            db_session, user, question_text_template="QT1?"
        )
        qt2 = await create_test_question_template(
            db_session, user, question_text_template="QT2?"
        )
        qt3 = await create_test_question_template(
            db_session, user, question_text_template="QT3?"
        )
        await db_session.commit()

        # Link question templates in specific order directly via DB
        await link_question_template_to_assessment_template(
            db_session, template.id, qt1.id, order=0
        )
        await link_question_template_to_assessment_template(
            db_session, template.id, qt2.id, order=1
        )
        await link_question_template_to_assessment_template(
            db_session, template.id, qt3.id, order=2
        )
        await db_session.commit()

        response = await test_client.get(f"/assessment-templates/{template.id}")

        assert response.status_code == 200
        data = response.json()
        assert len(data["question_templates"]) == 3
        # Verify order
        assert data["question_templates"][0]["question_text_template"] == "QT1?"
        assert data["question_templates"][0]["order"] == 0
        assert data["question_templates"][1]["question_text_template"] == "QT2?"
        assert data["question_templates"][1]["order"] == 1
        assert data["question_templates"][2]["question_text_template"] == "QT3?"
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

    @pytest.mark.asyncio
    async def test_get_public_template_by_non_owner(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test that authenticated non-collaborators can access public assessment templates."""
        from edcraft_backend.models.enums import ResourceVisibility

        template = await create_test_assessment_template(
            db_session, user, title="Public Template"
        )
        template.visibility = ResourceVisibility.PUBLIC
        await db_session.commit()

        from tests.conftest import _create_test_client

        async with _create_test_client(db_session) as client2:
            _ = await create_and_login_user(
                client2, db_session, email="at_viewer@test.com"
            )
            response = await client2.get(f"/assessment-templates/{template.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(template.id)
        assert data["visibility"] == "public"

    @pytest.mark.asyncio
    async def test_get_private_template_by_non_owner_fails(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test that authenticated non-collaborators cannot access private assessment templates."""
        template = await create_test_assessment_template(
            db_session, user, title="Private Template"
        )
        await db_session.commit()

        from tests.conftest import _create_test_client

        async with _create_test_client(db_session) as client2:
            _ = await create_and_login_user(
                client2, db_session, email="at_noviewer@test.com"
            )
            response = await client2.get(f"/assessment-templates/{template.id}")

        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_get_public_template_by_unauthenticated_user(
        self, unauth_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test that unauthenticated users can access public assessment templates."""
        from edcraft_backend.models.enums import ResourceVisibility

        template = await create_test_assessment_template(
            db_session, user, title="Public Template"
        )
        template.visibility = ResourceVisibility.PUBLIC
        await db_session.commit()

        response = await unauth_client.get(f"/assessment-templates/{template.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(template.id)
        assert data["visibility"] == "public"

    @pytest.mark.asyncio
    async def test_get_private_template_by_unauthenticated_user_fails(
        self, unauth_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test that unauthenticated users cannot access private assessment templates."""
        template = await create_test_assessment_template(
            db_session, user, title="Private Template"
        )
        await db_session.commit()

        response = await unauth_client.get(f"/assessment-templates/{template.id}")

        assert response.status_code == 403


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

    @pytest.mark.asyncio
    async def test_update_assessment_template_visibility(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test that owner can update assessment template visibility."""
        template = await create_test_assessment_template(db_session, user)
        await db_session.commit()

        response = await test_client.patch(
            f"/assessment-templates/{template.id}", json={"visibility": "public"}
        )

        assert response.status_code == 200
        assert response.json()["visibility"] == "public"

    @pytest.mark.asyncio
    async def test_editor_can_update_assessment_template(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test that an editor collaborator can PATCH the assessment template."""
        other_user = await create_test_user(
            db_session, email="at_owner_edit@test.com"
        )
        template = await create_test_assessment_template(
            db_session, other_user, title="Original Title"
        )
        await db_session.commit()

        await create_collaborator(
            db_session,
            ResourceType.ASSESSMENT_TEMPLATE,
            template.id,
            user,
            CollaboratorRole.EDITOR,
        )
        await db_session.commit()

        response = await test_client.patch(
            f"/assessment-templates/{template.id}",
            json={"title": "Updated By Editor"},
        )

        assert response.status_code == 200
        assert response.json()["title"] == "Updated By Editor"

    @pytest.mark.asyncio
    async def test_viewer_cannot_update_assessment_template_returns_403(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test that a viewer collaborator cannot PATCH the assessment template (403)."""
        other_user = await create_test_user(
            db_session, email="at_owner_viewer@test.com"
        )
        template = await create_test_assessment_template(
            db_session, other_user, title="Original Title"
        )
        await db_session.commit()

        await create_collaborator(
            db_session,
            ResourceType.ASSESSMENT_TEMPLATE,
            template.id,
            user,
            CollaboratorRole.VIEWER,
        )
        await db_session.commit()

        response = await test_client.patch(
            f"/assessment-templates/{template.id}",
            json={"title": "Should Fail"},
        )

        assert response.status_code == 403


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
                "question_text_template": "What is 2+2?",
                "text_template_type": "basic",
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
                "code_info": MINIMAL_CODE_INFO,
            },
            "order": 0,
        }
        response = await test_client.post(
            f"/assessment-templates/{template.id}/question-templates", json=qt_data
        )

        assert response.status_code == 201
        data = response.json()
        assert len(data["question_templates"]) == 1
        assert data["question_templates"][0]["question_text_template"] == "What is 2+2?"
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
                "question_text_template": "Question 1?",
                "text_template_type": "basic",
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
                "code_info": MINIMAL_CODE_INFO,
            },
            "order": 0,
        }
        await test_client.post(
            f"/assessment-templates/{template.id}/question-templates", json=qt_data_1
        )

        qt_data_2: dict[str, Any] = {
            "question_template": {
                "question_type": "mcq",
                "question_text_template": "Question 2?",
                "text_template_type": "basic",
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
                "code_info": MINIMAL_CODE_INFO,
            },
            "order": 1,
        }
        await test_client.post(
            f"/assessment-templates/{template.id}/question-templates", json=qt_data_2
        )

        qt_data_3: dict[str, Any] = {
            "question_template": {
                "question_type": "mcq",
                "question_text_template": "Question 3?",
                "text_template_type": "basic",
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
                "code_info": MINIMAL_CODE_INFO,
            },
            "order": 2,
        }
        response = await test_client.post(
            f"/assessment-templates/{template.id}/question-templates", json=qt_data_3
        )

        assert response.status_code == 201
        data = response.json()
        assert len(data["question_templates"]) == 3
        assert data["question_templates"][0]["question_text_template"] == "Question 1?"
        assert data["question_templates"][1]["question_text_template"] == "Question 2?"
        assert data["question_templates"][2]["question_text_template"] == "Question 3?"

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
                "question_text_template": "Test question?",
                "text_template_type": "basic",
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
                "code_info": MINIMAL_CODE_INFO,
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
                "question_text_template": "Test question?",
                "text_template_type": "basic",
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
                "code_info": MINIMAL_CODE_INFO,
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
                "question_text_template": "Question Template 1?",
                "text_template_type": "basic",
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
                "code_info": MINIMAL_CODE_INFO,
            },
            "order": 0,
        }
        await test_client.post(
            f"/assessment-templates/{template.id}/question-templates", json=qt1_data
        )

        qt2_data: dict[str, Any] = {
            "question_template": {
                "question_type": "mcq",
                "question_text_template": "Question Template 2?",
                "text_template_type": "basic",
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
                "code_info": MINIMAL_CODE_INFO,
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
        assert templates[0]["question_text_template"] == "Question Template 2?"
        assert templates[0]["order"] == 0
        assert templates[1]["question_text_template"] == "Question Template 1?"
        assert templates[1]["order"] == 1


@pytest.mark.integration
@pytest.mark.assessment_templates
class TestLinkQuestionTemplateToAssessmentTemplate:
    """Tests for POST /assessment-templates/{template_id}/question-templates/link endpoint."""

    @pytest.mark.asyncio
    async def test_link_question_template_to_assessment_template_success(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test linking question template to assessment template creates a copy."""
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
        assert data["question_templates"][0]["id"] != str(qt.id)
        assert data["question_templates"][0]["linked_from_template_id"] == str(qt.id)
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
        assert data["question_templates"][0]["linked_from_template_id"] == str(qt1.id)
        assert data["question_templates"][0]["id"] != str(qt1.id)
        assert data["question_templates"][1]["linked_from_template_id"] == str(qt2.id)
        assert data["question_templates"][1]["id"] != str(qt2.id)
        assert data["question_templates"][2]["linked_from_template_id"] == str(qt3.id)
        assert data["question_templates"][2]["id"] != str(qt3.id)

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
            db_session, user, question_text_template="QT1?"
        )
        qt2 = await create_test_question_template(
            db_session, user, question_text_template="QT2?"
        )
        await db_session.commit()

        await link_question_template_to_assessment_template(
            db_session, template.id, qt1.id, order=0
        )
        await db_session.commit()

        response = await test_client.post(
            f"/assessment-templates/{template.id}/question-templates/link",
            json={"question_template_id": str(qt2.id), "order": 0},
        )

        assert response.status_code == 201
        data = response.json()
        templates = data["question_templates"]

        assert len(templates) == 2
        assert templates[0]["question_text_template"] == "QT2?"
        assert templates[0]["order"] == 0
        assert templates[1]["question_text_template"] == "QT1?"
        assert templates[1]["order"] == 1

    @pytest.mark.asyncio
    async def test_link_question_template_insert_in_middle(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test linking question template in middle shifts templates at/after position down."""
        template = await create_test_assessment_template(db_session, user)
        qt1 = await create_test_question_template(
            db_session, user, question_text_template="QT1?"
        )
        qt2 = await create_test_question_template(
            db_session, user, question_text_template="QT2?"
        )
        qt3 = await create_test_question_template(
            db_session, user, question_text_template="QT3?"
        )
        qt4 = await create_test_question_template(
            db_session, user, question_text_template="QT4?"
        )
        qt_new = await create_test_question_template(
            db_session, user, question_text_template="QT_NEW?"
        )
        await db_session.commit()

        # Add initial question templates
        for i, qt in enumerate([qt1, qt2, qt3, qt4]):
            await link_question_template_to_assessment_template(
                db_session, template.id, qt.id, order=i
            )
        await db_session.commit()

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
        assert templates[0]["question_text_template"] == "QT1?"
        assert templates[0]["order"] == 0
        assert templates[1]["question_text_template"] == "QT2?"
        assert templates[1]["order"] == 1
        assert templates[2]["question_text_template"] == "QT_NEW?"
        assert templates[2]["order"] == 2
        assert templates[3]["question_text_template"] == "QT3?"
        assert templates[3]["order"] == 3
        assert templates[4]["question_text_template"] == "QT4?"
        assert templates[4]["order"] == 4

    @pytest.mark.asyncio
    async def test_link_question_template_with_order_exceeding_count(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test linking with order > count fails with validation error."""
        template = await create_test_assessment_template(db_session, user)
        qt1 = await create_test_question_template(
            db_session, user, question_text_template="QT1?"
        )
        qt2 = await create_test_question_template(
            db_session, user, question_text_template="QT2?"
        )
        qt_new = await create_test_question_template(
            db_session, user, question_text_template="QT_NEW?"
        )
        await db_session.commit()

        # Add two question templates (count=2)
        await link_question_template_to_assessment_template(
            db_session, template.id, qt1.id, order=0
        )
        await link_question_template_to_assessment_template(
            db_session, template.id, qt2.id, order=1
        )
        await db_session.commit()

        response = await test_client.post(
            f"/assessment-templates/{template.id}/question-templates/link",
            json={"question_template_id": str(qt_new.id), "order": 10},
        )

        assert response.status_code == 400
        assert "Order must be between 0 and 2" in response.json()["detail"]
        assert "Omit order to append" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_link_question_template_from_other_template_as_viewer(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test that a viewer on a source assessment template can link its question templates."""
        owner2 = await create_test_user(db_session)
        source_template = await create_test_assessment_template(db_session, owner2)
        qt = await create_test_question_template(
            db_session, owner2, question_text_template="Source QT?"
        )
        await link_question_template_to_assessment_template(
            db_session, source_template.id, qt.id
        )
        await create_collaborator(
            db_session,
            ResourceType.ASSESSMENT_TEMPLATE,
            source_template.id,
            user,
            CollaboratorRole.VIEWER,
        )
        dest_template = await create_test_assessment_template(db_session, user)
        await db_session.commit()

        response = await test_client.post(
            f"/assessment-templates/{dest_template.id}/question-templates/link",
            json={"question_template_id": str(qt.id)},
        )

        assert response.status_code == 201
        data = response.json()
        assert len(data["question_templates"]) == 1
        assert data["question_templates"][0]["linked_from_template_id"] == str(qt.id)
        assert data["question_templates"][0]["question_text_template"] == "Source QT?"

    @pytest.mark.asyncio
    async def test_link_question_template_without_access_returns_403(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test that linking a question template without access returns 403."""
        owner2 = await create_test_user(db_session)
        private_template = await create_test_assessment_template(db_session, owner2)
        qt = await create_test_question_template(db_session, owner2)
        await link_question_template_to_assessment_template(
            db_session, private_template.id, qt.id
        )
        dest_template = await create_test_assessment_template(db_session, user)
        await db_session.commit()

        response = await test_client.post(
            f"/assessment-templates/{dest_template.id}/question-templates/link",
            json={"question_template_id": str(qt.id)},
        )

        assert response.status_code == 403


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
        await link_question_template_to_assessment_template(
            db_session, template.id, qt.id, order=0
        )
        await db_session.commit()
        copy_id = str(qt.id)

        # Remove question template
        response = await test_client.delete(
            f"/assessment-templates/{template.id}/question-templates/{copy_id}"
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
        await link_question_template_to_assessment_template(
            db_session, template.id, qt1.id, order=0
        )
        await link_question_template_to_assessment_template(
            db_session, template.id, qt2.id, order=1
        )
        await db_session.commit()
        copy1_id = str(qt1.id)
        copy2_id = str(qt2.id)

        # Remove first question template
        await test_client.delete(
            f"/assessment-templates/{template.id}/question-templates/{copy1_id}"
        )

        # Verify only second question template remains
        response = await test_client.get(f"/assessment-templates/{template.id}")
        data = response.json()
        assert len(data["question_templates"]) == 1
        assert data["question_templates"][0]["id"] == copy2_id

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
            db_session, user, question_text_template="QT1?"
        )
        qt2 = await create_test_question_template(
            db_session, user, question_text_template="QT2?"
        )
        qt3 = await create_test_question_template(
            db_session, user, question_text_template="QT3?"
        )
        await db_session.commit()

        await link_question_template_to_assessment_template(
            db_session, template.id, qt1.id, order=0
        )
        await link_question_template_to_assessment_template(
            db_session, template.id, qt2.id, order=1
        )
        await link_question_template_to_assessment_template(
            db_session, template.id, qt3.id, order=2
        )
        await db_session.commit()
        copy2_id = str(qt2.id)

        await test_client.delete(
            f"/assessment-templates/{template.id}/question-templates/{copy2_id}"
        )

        response = await test_client.get(f"/assessment-templates/{template.id}")
        data = response.json()

        assert len(data["question_templates"]) == 2
        assert data["question_templates"][0]["question_text_template"] == "QT1?"
        assert data["question_templates"][0]["order"] == 0
        assert data["question_templates"][1]["question_text_template"] == "QT3?"
        assert data["question_templates"][1]["order"] == 1


@pytest.mark.integration
@pytest.mark.assessment_templates
class TestSyncQuestionTemplateInAssessmentTemplate:
    """
    Tests for
    POST /assessment-templates/{template_id}/question-templates/{question_template_id}/sync
    endpoint.
    """

    @pytest.mark.asyncio
    async def test_sync_updates_copy_from_source(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test that sync overwrites copy content with the current source content."""
        template = await create_test_assessment_template(db_session, user)
        source = await create_test_question_template(
            db_session, user, question_text_template="Original text?"
        )
        await db_session.commit()

        # Link (creates copy)
        link_resp = await test_client.post(
            f"/assessment-templates/{template.id}/question-templates/link",
            json={"question_template_id": str(source.id)},
        )
        copy_id = link_resp.json()["question_templates"][0]["id"]

        # Edit the copy independently
        await test_client.patch(
            f"/question-templates/{copy_id}",
            json={"question_text_template": "Edited in assessment template?"},
        )

        # Edit the source
        await test_client.patch(
            f"/question-templates/{str(source.id)}",
            json={"question_text_template": "Updated source text?"},
        )

        # Sync the copy
        response = await test_client.post(
            f"/assessment-templates/{template.id}/question-templates/{copy_id}/sync"
        )

        assert response.status_code == 200
        question_templates = response.json()["question_templates"]
        copy = next(qt for qt in question_templates if qt["id"] == copy_id)
        assert copy["question_text_template"] == "Updated source text?"
        assert copy["linked_from_template_id"] == str(source.id)

    @pytest.mark.asyncio
    async def test_sync_without_source_link_returns_400(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test that syncing a question template with no source link returns 400."""
        template = await create_test_assessment_template(db_session, user)
        qt = await create_test_question_template(db_session, user)
        await db_session.commit()

        await link_question_template_to_assessment_template(
            db_session, template.id, qt.id, order=0
        )
        await db_session.commit()

        response = await test_client.post(
            f"/assessment-templates/{template.id}/question-templates/{qt.id}/sync"
        )

        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_sync_question_template_not_in_assessment_template_returns_404(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test that syncing a question template not in the assessment template returns 404."""
        import uuid

        template = await create_test_assessment_template(db_session, user)
        await db_session.commit()

        response = await test_client.post(
            f"/assessment-templates/{template.id}/question-templates/{uuid.uuid4()}/sync"
        )

        assert response.status_code == 404


@pytest.mark.integration
@pytest.mark.assessment_templates
class TestUnlinkQuestionTemplateInAssessmentTemplate:
    """
    Tests for
    POST /assessment-templates/{template_id}/question-templates/{question_template_id}/unlink
    endpoint.
    """

    @pytest.mark.asyncio
    async def test_unlink_severs_source_reference(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test that unlink sets linked_from_template_id to null."""
        template = await create_test_assessment_template(db_session, user)
        source = await create_test_question_template(
            db_session, user, question_text_template="Source text?"
        )
        await db_session.commit()

        link_resp = await test_client.post(
            f"/assessment-templates/{template.id}/question-templates/link",
            json={"question_template_id": str(source.id)},
        )
        copy_id = link_resp.json()["question_templates"][0]["id"]

        response = await test_client.post(
            f"/assessment-templates/{template.id}/question-templates/{copy_id}/unlink"
        )

        assert response.status_code == 200
        question_templates = response.json()["question_templates"]
        copy = next(qt for qt in question_templates if qt["id"] == copy_id)
        assert copy["linked_from_template_id"] is None
        assert copy["question_text_template"] == "Source text?"

    @pytest.mark.asyncio
    async def test_unlink_question_template_not_in_assessment_template_returns_404(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test that unlinking a question template not in the assessment template returns 404."""
        import uuid

        template = await create_test_assessment_template(db_session, user)
        await db_session.commit()

        response = await test_client.post(
            f"/assessment-templates/{template.id}/question-templates/{uuid.uuid4()}/unlink"
        )

        assert response.status_code == 404


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
            db_session, user, question_text_template="QT1?"
        )
        qt2 = await create_test_question_template(
            db_session, user, question_text_template="QT2?"
        )
        qt3 = await create_test_question_template(
            db_session, user, question_text_template="QT3?"
        )
        await db_session.commit()

        # Link question templates in initial order
        await link_question_template_to_assessment_template(
            db_session, template.id, qt1.id, order=0
        )
        await link_question_template_to_assessment_template(
            db_session, template.id, qt2.id, order=1
        )
        await link_question_template_to_assessment_template(
            db_session, template.id, qt3.id, order=2
        )
        await db_session.commit()
        copy1_id = str(qt1.id)
        copy2_id = str(qt2.id)
        copy3_id = str(qt3.id)

        # Reorder: reverse the order
        reorder_data: dict[str, Any] = {
            "question_template_orders": [
                {"question_template_id": copy3_id, "order": 0},
                {"question_template_id": copy2_id, "order": 1},
                {"question_template_id": copy1_id, "order": 2},
            ]
        }
        response = await test_client.patch(
            f"/assessment-templates/{template.id}/question-templates/reorder",
            json=reorder_data,
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["question_templates"]) == 3
        assert data["question_templates"][0]["question_text_template"] == "QT3?"
        assert data["question_templates"][1]["question_text_template"] == "QT2?"
        assert data["question_templates"][2]["question_text_template"] == "QT1?"

    @pytest.mark.asyncio
    async def test_reorder_question_templates_requires_all_questions(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test reordering only some question templates (partial update) fails."""
        template = await create_test_assessment_template(db_session, user)
        qt1 = await create_test_question_template(db_session, user)
        qt2 = await create_test_question_template(db_session, user)
        qt3 = await create_test_question_template(db_session, user)
        await db_session.commit()

        # Link question templates
        await link_question_template_to_assessment_template(
            db_session, template.id, qt1.id, order=0
        )
        await link_question_template_to_assessment_template(
            db_session, template.id, qt2.id, order=1
        )
        await link_question_template_to_assessment_template(
            db_session, template.id, qt3.id, order=2
        )
        await db_session.commit()
        copy1_id = str(qt1.id)
        copy2_id = str(qt2.id)

        # Reorder: only swap first two
        reorder_data: dict[str, Any] = {
            "question_template_orders": [
                {"question_template_id": copy2_id, "order": 0},
                {"question_template_id": copy1_id, "order": 1},
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
            db_session, user, question_text_template="QT1?"
        )
        qt2 = await create_test_question_template(
            db_session, user, question_text_template="QT2?"
        )
        qt3 = await create_test_question_template(
            db_session, user, question_text_template="QT3?"
        )
        await db_session.commit()

        # Add question templates
        await link_question_template_to_assessment_template(
            db_session, template.id, qt1.id, order=0
        )
        await link_question_template_to_assessment_template(
            db_session, template.id, qt2.id, order=1
        )
        await link_question_template_to_assessment_template(
            db_session, template.id, qt3.id, order=2
        )
        await db_session.commit()
        copy1_id = str(qt1.id)
        copy2_id = str(qt2.id)
        copy3_id = str(qt3.id)

        # Reorder with gaps (order: 5, 10, 100)
        reorder_data: dict[str, Any] = {
            "question_template_orders": [
                {"question_template_id": copy1_id, "order": 100},
                {"question_template_id": copy2_id, "order": 5},
                {"question_template_id": copy3_id, "order": 10},
            ]
        }
        response = await test_client.patch(
            f"/assessment-templates/{template.id}/question-templates/reorder",
            json=reorder_data,
        )

        assert response.status_code == 200
        data = response.json()

        assert data["question_templates"][0]["question_text_template"] == "QT2?"
        assert data["question_templates"][0]["order"] == 0
        assert data["question_templates"][1]["question_text_template"] == "QT3?"
        assert data["question_templates"][1]["order"] == 1
        assert data["question_templates"][2]["question_text_template"] == "QT1?"
        assert data["question_templates"][2]["order"] == 2
