"""Integration tests for Question Template Bank API endpoints."""

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from edcraft_backend.models.enums import CollaboratorRole, ResourceType
from edcraft_backend.models.question_template import QuestionTemplate
from edcraft_backend.models.user import User
from tests.factories import (
    create_and_login_user,
    create_collaborator,
    create_question_template_bank_with_templates,
    create_test_folder,
    create_test_question_template,
    create_test_question_template_bank,
    create_test_user,
    link_question_template_to_question_template_bank,
)


@pytest.mark.integration
@pytest.mark.question_template_banks
class TestCreateQuestionTemplateBank:
    """Tests for POST /question-template-banks endpoint."""

    @pytest.mark.asyncio
    async def test_create_question_template_bank_with_folder(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test creating a question template bank linked to a folder."""
        folder = await create_test_folder(db_session, user)
        await db_session.commit()

        response = await test_client.post(
            "/question-template-banks",
            json={
                "folder_id": str(folder.id),
                "title": "My Question Template Bank",
                "description": "A collection of question templates",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "My Question Template Bank"
        assert data["description"] == "A collection of question templates"
        assert data["folder_id"] == str(folder.id)
        assert data["owner_id"] == str(user.id)
        assert "id" in data
        assert "created_at" in data

    @pytest.mark.asyncio
    async def test_create_question_template_bank_nonexistent_folder(
        self, test_client: AsyncClient, user: User
    ) -> None:
        """Test creating a question template bank with non-existent folder."""
        import uuid

        fake_folder_id = str(uuid.uuid4())
        response = await test_client.post(
            "/question-template-banks",
            json={
                "folder_id": fake_folder_id,
                "title": "My Question Template Bank",
            },
        )

        assert response.status_code == 404


@pytest.mark.integration
@pytest.mark.question_template_banks
class TestListQuestionTemplateBanks:
    """Tests for GET /question-template-banks endpoint."""

    @pytest.mark.asyncio
    async def test_list_question_template_banks_success(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test listing all question template banks for a user."""
        bank1 = await create_test_question_template_bank(
            db_session, user, title="Bank 1"
        )
        bank2 = await create_test_question_template_bank(
            db_session, user, title="Bank 2"
        )
        await db_session.commit()

        response = await test_client.get("/question-template-banks")

        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 2
        bank_ids = [b["id"] for b in data]
        assert str(bank1.id) in bank_ids
        assert str(bank2.id) in bank_ids

    @pytest.mark.asyncio
    async def test_list_question_template_banks_filter_by_folder(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test listing question template banks filtered by folder."""
        folder1 = await create_test_folder(db_session, user, name="Folder 1")
        folder2 = await create_test_folder(db_session, user, name="Folder 2")

        bank1 = await create_test_question_template_bank(
            db_session, user, folder=folder1, title="Bank in Folder 1"
        )
        await create_test_question_template_bank(
            db_session, user, folder=folder2, title="Bank in Folder 2"
        )
        await db_session.commit()

        response = await test_client.get(
            f"/question-template-banks?folder_id={folder1.id}"
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["folder_id"] == str(folder1.id)
        assert data[0]["id"] == str(bank1.id)

    @pytest.mark.asyncio
    async def test_list_question_template_banks_excludes_soft_deleted(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test that soft-deleted question template banks are excluded."""
        active_bank = await create_test_question_template_bank(
            db_session, user, title="To Delete"
        )
        deleted_bank = await create_test_question_template_bank(
            db_session, user, title="To Keep"
        )
        await db_session.commit()

        # Soft delete the bank
        await test_client.delete(f"/question-template-banks/{active_bank.id}")

        # List should not include deleted bank
        response = await test_client.get("/question-template-banks")
        assert response.status_code == 200
        data = response.json()
        bank_ids = [b["id"] for b in data]
        assert str(active_bank.id) not in bank_ids
        assert str(deleted_bank.id) in bank_ids

    @pytest.mark.asyncio
    async def test_collab_filter_owned_returns_only_owned(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """collab_filter=owned returns only banks owned by user."""
        owned_bank = await create_test_question_template_bank(db_session, user)
        other_owner = await create_test_user(
            db_session, email="other_owner_qtb@test.com"
        )
        shared_bank = await create_test_question_template_bank(db_session, other_owner)
        await db_session.commit()

        await create_collaborator(
            db_session,
            ResourceType.QUESTION_TEMPLATE_BANK,
            shared_bank.id,
            user,
            CollaboratorRole.EDITOR,
        )
        await db_session.commit()

        response = await test_client.get(
            "/question-template-banks", params={"collab_filter": "owned"}
        )

        assert response.status_code == 200
        ids = [b["id"] for b in response.json()]
        assert str(owned_bank.id) in ids
        assert str(shared_bank.id) not in ids

    @pytest.mark.asyncio
    async def test_collab_filter_shared_returns_only_shared(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """collab_filter=shared returns only banks where user is non-owner collaborator."""
        owned_bank = await create_test_question_template_bank(db_session, user)
        other_owner = await create_test_user(
            db_session, email="other_owner_shared_qtb@test.com"
        )
        shared_bank = await create_test_question_template_bank(db_session, other_owner)
        await db_session.commit()

        await create_collaborator(
            db_session,
            ResourceType.QUESTION_TEMPLATE_BANK,
            shared_bank.id,
            user,
            CollaboratorRole.VIEWER,
        )
        await db_session.commit()

        response = await test_client.get(
            "/question-template-banks", params={"collab_filter": "shared"}
        )

        assert response.status_code == 200
        ids = [b["id"] for b in response.json()]
        assert str(shared_bank.id) in ids
        assert str(owned_bank.id) not in ids

    @pytest.mark.asyncio
    async def test_collab_filter_all_returns_both(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """collab_filter=all (default) returns both owned and shared banks."""
        owned_bank = await create_test_question_template_bank(db_session, user)
        other_owner = await create_test_user(
            db_session, email="other_owner_all_qtb@test.com"
        )
        shared_bank = await create_test_question_template_bank(db_session, other_owner)
        await db_session.commit()

        await create_collaborator(
            db_session,
            ResourceType.QUESTION_TEMPLATE_BANK,
            shared_bank.id,
            user,
            CollaboratorRole.EDITOR,
        )
        await db_session.commit()

        response = await test_client.get("/question-template-banks")

        assert response.status_code == 200
        ids = [b["id"] for b in response.json()]
        assert str(owned_bank.id) in ids
        assert str(shared_bank.id) in ids


@pytest.mark.integration
@pytest.mark.question_template_banks
class TestGetQuestionTemplateBank:
    """Tests for GET /question-template-banks/{id} endpoint."""

    @pytest.mark.asyncio
    async def test_get_question_template_bank_success(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test retrieving a single question template bank."""
        bank = await create_test_question_template_bank(
            db_session, user, title="Test Bank"
        )
        await db_session.commit()

        response = await test_client.get(f"/question-template-banks/{bank.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(bank.id)
        assert data["title"] == "Test Bank"
        assert "question_templates" in data

    @pytest.mark.asyncio
    async def test_get_question_template_bank_with_templates(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test getting a question template bank with linked templates."""
        bank, _ = await create_question_template_bank_with_templates(
            db_session, user, num_templates=3
        )
        await db_session.commit()

        response = await test_client.get(f"/question-template-banks/{bank.id}")

        assert response.status_code == 200
        data = response.json()
        assert len(data["question_templates"]) == 3

    @pytest.mark.asyncio
    async def test_get_question_template_bank_not_found(
        self, test_client: AsyncClient, user: User
    ) -> None:
        """Test getting a non-existent question template bank."""
        import uuid

        fake_id = str(uuid.uuid4())
        response = await test_client.get(f"/question-template-banks/{fake_id}")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_question_template_bank_soft_deleted_returns_404(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test that soft-deleted banks return 404."""
        bank = await create_test_question_template_bank(db_session, user)
        await db_session.commit()

        # Soft delete
        await test_client.delete(f"/question-template-banks/{bank.id}")

        # Should return 404
        response = await test_client.get(f"/question-template-banks/{bank.id}")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_public_bank_by_non_owner(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test that authenticated non-collaborators can access public question template banks."""
        from edcraft_backend.models.enums import ResourceVisibility

        bank = await create_test_question_template_bank(
            db_session, user, title="Public Bank"
        )
        bank.visibility = ResourceVisibility.PUBLIC
        await db_session.commit()

        from tests.conftest import _create_test_client

        async with _create_test_client(db_session) as client2:
            _ = await create_and_login_user(
                client2, db_session, email="qtb_viewer@test.com"
            )
            response = await client2.get(f"/question-template-banks/{bank.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(bank.id)
        assert data["visibility"] == "public"

    @pytest.mark.asyncio
    async def test_get_private_bank_by_non_owner_fails(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test that authenticated non-collaborators cannot access private qt banks."""
        bank = await create_test_question_template_bank(
            db_session, user, title="Private Bank"
        )
        await db_session.commit()

        from tests.conftest import _create_test_client

        async with _create_test_client(db_session) as client2:
            _ = await create_and_login_user(
                client2, db_session, email="qtb_noviewer@test.com"
            )
            response = await client2.get(f"/question-template-banks/{bank.id}")

        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_get_public_bank_by_unauthenticated_user(
        self, unauth_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test that unauthenticated users can access public question template banks."""
        from edcraft_backend.models.enums import ResourceVisibility

        bank = await create_test_question_template_bank(
            db_session, user, title="Public Bank"
        )
        bank.visibility = ResourceVisibility.PUBLIC
        await db_session.commit()

        response = await unauth_client.get(f"/question-template-banks/{bank.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(bank.id)
        assert data["visibility"] == "public"

    @pytest.mark.asyncio
    async def test_get_private_bank_by_unauthenticated_user_fails(
        self, unauth_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test that unauthenticated users cannot access private question template banks."""
        bank = await create_test_question_template_bank(
            db_session, user, title="Private Bank"
        )
        await db_session.commit()

        response = await unauth_client.get(f"/question-template-banks/{bank.id}")

        assert response.status_code == 403


@pytest.mark.integration
@pytest.mark.question_template_banks
class TestUpdateQuestionTemplateBank:
    """Tests for PATCH /question-template-banks/{id} endpoint."""

    @pytest.mark.asyncio
    async def test_update_question_template_bank_title(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test updating a question template bank's title."""
        bank = await create_test_question_template_bank(
            db_session, user, title="Old Title"
        )
        await db_session.commit()

        response = await test_client.patch(
            f"/question-template-banks/{bank.id}",
            json={"title": "New Title"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "New Title"

    @pytest.mark.asyncio
    async def test_update_question_template_bank_description(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test updating a question template bank's description."""
        bank = await create_test_question_template_bank(db_session, user)
        await db_session.commit()

        response = await test_client.patch(
            f"/question-template-banks/{bank.id}",
            json={"description": "Updated description"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["description"] == "Updated description"

    @pytest.mark.asyncio
    async def test_update_question_template_bank_move_to_different_folder(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test moving a question template bank to a different folder."""
        folder1 = await create_test_folder(db_session, user, name="Folder 1")
        folder2 = await create_test_folder(db_session, user, name="Folder 2")
        bank = await create_test_question_template_bank(
            db_session, user, folder=folder1
        )
        await db_session.commit()

        response = await test_client.patch(
            f"/question-template-banks/{bank.id}",
            json={"folder_id": str(folder2.id)},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["folder_id"] == str(folder2.id)

    @pytest.mark.asyncio
    async def test_update_question_template_bank_not_found(
        self, test_client: AsyncClient, user: User
    ) -> None:
        """Test updating a non-existent question template bank."""
        import uuid

        fake_id = str(uuid.uuid4())
        response = await test_client.patch(
            f"/question-template-banks/{fake_id}",
            json={"title": "New Title"},
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_question_template_bank_visibility(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test that owner can update question template bank visibility."""
        bank = await create_test_question_template_bank(db_session, user)
        await db_session.commit()

        response = await test_client.patch(
            f"/question-template-banks/{bank.id}", json={"visibility": "public"}
        )

        assert response.status_code == 200
        assert response.json()["visibility"] == "public"

    @pytest.mark.asyncio
    async def test_editor_can_update_question_template_bank(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test that an editor collaborator can PATCH the question template bank."""
        other_user = await create_test_user(
            db_session, email="qtb_owner_edit@test.com"
        )
        bank = await create_test_question_template_bank(
            db_session, other_user, title="Original Title"
        )
        await db_session.commit()

        await create_collaborator(
            db_session,
            ResourceType.QUESTION_TEMPLATE_BANK,
            bank.id,
            user,
            CollaboratorRole.EDITOR,
        )
        await db_session.commit()

        response = await test_client.patch(
            f"/question-template-banks/{bank.id}",
            json={"title": "Updated By Editor"},
        )

        assert response.status_code == 200
        assert response.json()["title"] == "Updated By Editor"

    @pytest.mark.asyncio
    async def test_viewer_cannot_update_question_template_bank_returns_403(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test that a viewer collaborator cannot PATCH the question template bank (403)."""
        other_user = await create_test_user(
            db_session, email="qtb_owner_viewer@test.com"
        )
        bank = await create_test_question_template_bank(
            db_session, other_user, title="Original Title"
        )
        await db_session.commit()

        await create_collaborator(
            db_session,
            ResourceType.QUESTION_TEMPLATE_BANK,
            bank.id,
            user,
            CollaboratorRole.VIEWER,
        )
        await db_session.commit()

        response = await test_client.patch(
            f"/question-template-banks/{bank.id}",
            json={"title": "Should Fail"},
        )

        assert response.status_code == 403


@pytest.mark.integration
@pytest.mark.question_template_banks
class TestSoftDeleteQuestionTemplateBank:
    """Tests for DELETE /question-template-banks/{id} endpoint."""

    @pytest.mark.asyncio
    async def test_soft_delete_question_template_bank_success(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test soft deleting a question template bank."""
        bank = await create_test_question_template_bank(db_session, user)
        await db_session.commit()

        response = await test_client.delete(f"/question-template-banks/{bank.id}")
        assert response.status_code == 204

        await db_session.refresh(bank)
        assert bank.deleted_at is not None

    @pytest.mark.asyncio
    async def test_soft_delete_question_template_bank_not_in_list(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test that a soft-deleted question template bank is not in the list."""
        bank = await create_test_question_template_bank(db_session, user)
        await db_session.commit()

        # Soft delete the bank
        response = await test_client.delete(f"/question-template-banks/{bank.id}")
        assert response.status_code == 204

        # List should not include deleted bank
        response = await test_client.get("/question-template-banks")

        assert response.status_code == 200
        data = response.json()
        bank_ids = [b["id"] for b in data]
        assert str(bank.id) not in bank_ids

    @pytest.mark.asyncio
    async def test_soft_delete_question_template_bank_not_found(
        self, test_client: AsyncClient, user: User
    ) -> None:
        """Test deleting a non-existent question template bank."""
        import uuid

        fake_id = str(uuid.uuid4())
        response = await test_client.delete(f"/question-template-banks/{fake_id}")
        assert response.status_code == 404


@pytest.mark.integration
@pytest.mark.question_template_banks
class TestInsertQuestionTemplateIntoBank:
    """Tests for POST /question-template-banks/{id}/question-templates endpoint."""

    @pytest.mark.asyncio
    async def test_insert_question_template_success(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test inserting a new question template into a bank."""
        bank = await create_test_question_template_bank(db_session, user)
        await db_session.commit()

        response = await test_client.post(
            f"/question-template-banks/{bank.id}/question-templates",
            json={
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
                },
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert len(data["question_templates"]) == 1
        assert data["question_templates"][0]["question_text_template"] == "What is 2+2?"

    @pytest.mark.asyncio
    async def test_insert_question_template_bank_not_found(
        self, test_client: AsyncClient, user: User
    ) -> None:
        """Test inserting into a non-existent bank."""
        import uuid

        fake_id = str(uuid.uuid4())
        response = await test_client.post(
            f"/question-template-banks/{fake_id}/question-templates",
            json={
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
                },
            },
        )
        assert response.status_code == 404


@pytest.mark.integration
@pytest.mark.question_template_banks
class TestLinkQuestionTemplateToBank:
    """Tests for POST /question-template-banks/{id}/question-templates/link endpoint."""

    @pytest.mark.asyncio
    async def test_link_question_template_success(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test linking an existing question template to a bank creates a copy."""
        bank = await create_test_question_template_bank(db_session, user)
        template = await create_test_question_template(
            db_session, user, question_text_template="Existing template"
        )
        await db_session.commit()

        response = await test_client.post(
            f"/question-template-banks/{bank.id}/question-templates/link",
            json={"question_template_id": str(template.id)},
        )

        assert response.status_code == 201
        data = response.json()
        assert len(data["question_templates"]) == 1
        assert data["question_templates"][0]["id"] != str(template.id)
        assert data["question_templates"][0]["linked_from_template_id"] == str(
            template.id
        )

    @pytest.mark.asyncio
    async def test_link_question_template_not_found(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test linking a non-existent question template."""
        import uuid

        bank = await create_test_question_template_bank(db_session, user)
        await db_session.commit()

        fake_template_id = str(uuid.uuid4())
        response = await test_client.post(
            f"/question-template-banks/{bank.id}/question-templates/link",
            json={"question_template_id": fake_template_id},
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_link_question_template_bank_not_found(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test linking to a non-existent bank."""
        import uuid

        template = await create_test_question_template(db_session, user)
        await db_session.commit()

        fake_bank_id = str(uuid.uuid4())
        response = await test_client.post(
            f"/question-template-banks/{fake_bank_id}/question-templates/link",
            json={"question_template_id": str(template.id)},
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_link_question_template_from_other_bank_as_viewer(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test that a viewer on a source question template bank can link its templates."""
        owner2 = await create_test_user(db_session)
        source_bank = await create_test_question_template_bank(db_session, owner2)
        qt = await create_test_question_template(
            db_session, owner2, question_text_template="Source QT?"
        )
        await link_question_template_to_question_template_bank(
            db_session, source_bank.id, qt.id
        )
        await create_collaborator(
            db_session,
            ResourceType.QUESTION_TEMPLATE_BANK,
            source_bank.id,
            user,
            CollaboratorRole.VIEWER,
        )
        dest_bank = await create_test_question_template_bank(db_session, user)
        await db_session.commit()

        response = await test_client.post(
            f"/question-template-banks/{dest_bank.id}/question-templates/link",
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
        private_bank = await create_test_question_template_bank(db_session, owner2)
        qt = await create_test_question_template(db_session, owner2)
        await link_question_template_to_question_template_bank(
            db_session, private_bank.id, qt.id
        )
        dest_bank = await create_test_question_template_bank(db_session, user)
        await db_session.commit()

        response = await test_client.post(
            f"/question-template-banks/{dest_bank.id}/question-templates/link",
            json={"question_template_id": str(qt.id)},
        )

        assert response.status_code == 403


@pytest.mark.integration
@pytest.mark.question_template_banks
class TestRemoveQuestionTemplateFromBank:
    """Tests for DELETE /question-template-banks/{id}/question-templates/{template_id}."""

    @pytest.mark.asyncio
    async def test_remove_question_template_success(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test removing a question template from a bank."""
        bank, templates = await create_question_template_bank_with_templates(
            db_session, user, num_templates=3
        )
        template_to_remove = templates[0]
        await db_session.commit()

        response = await test_client.delete(
            f"/question-template-banks/{bank.id}/question-templates/{template_to_remove.id}"
        )

        assert response.status_code == 204

        # Verify association is removed
        template_to_remove_id = template_to_remove.id
        bank_id = bank.id
        db_session.expire_all()
        result = await db_session.execute(
            select(QuestionTemplate).where(QuestionTemplate.id == template_to_remove_id)
        )
        removed_template = result.scalar_one_or_none()
        if removed_template is not None:
            assert removed_template.question_template_bank_id != bank_id

    @pytest.mark.asyncio
    async def test_remove_question_template_preserves_others(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test that removing one template preserves others."""
        bank, templates = await create_question_template_bank_with_templates(
            db_session, user, num_templates=3
        )
        await db_session.commit()

        # Remove first template
        response = await test_client.delete(
            f"/question-template-banks/{bank.id}/question-templates/{templates[0].id}"
        )
        assert response.status_code == 204

        # Get bank and verify other templates remain
        response = await test_client.get(f"/question-template-banks/{bank.id}")
        data = response.json()
        assert len(data["question_templates"]) == 2
        template_ids = [t["id"] for t in data["question_templates"]]
        assert str(templates[1].id) in template_ids
        assert str(templates[2].id) in template_ids

    @pytest.mark.asyncio
    async def test_remove_question_template_not_found(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test removing a non-existent template."""
        import uuid

        bank = await create_test_question_template_bank(db_session, user)
        await db_session.commit()

        fake_template_id = str(uuid.uuid4())
        response = await test_client.delete(
            f"/question-template-banks/{bank.id}/question-templates/{fake_template_id}"
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_remove_question_template_bank_not_found(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test removing from a non-existent bank."""
        import uuid

        template = await create_test_question_template(db_session, user)
        await db_session.commit()

        fake_bank_id = str(uuid.uuid4())
        response = await test_client.delete(
            f"/question-template-banks/{fake_bank_id}/question-templates/{template.id}"
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_remove_question_template_cleans_up_orphans(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test that removing creates orphan cleanup."""
        bank, templates = await create_question_template_bank_with_templates(
            db_session, user, num_templates=1
        )
        template = templates[0]
        await db_session.commit()

        # Remove the only template
        response = await test_client.delete(
            f"/question-template-banks/{bank.id}/question-templates/{template.id}"
        )
        assert response.status_code == 204

        # Template should be soft-deleted (orphaned)
        result = await db_session.execute(
            select(QuestionTemplate).where(QuestionTemplate.id == template.id)
        )
        orphaned_template = result.scalar_one()
        await db_session.refresh(orphaned_template)
        assert orphaned_template.deleted_at is not None


@pytest.mark.integration
@pytest.mark.question_template_banks
class TestSyncQuestionTemplateInBank:
    """Tests for POST /question-template-banks/{id}/question-templates/{template_id}/sync."""

    @pytest.mark.asyncio
    async def test_sync_updates_copy_from_source(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test that sync overwrites copy content with the current source content."""
        bank = await create_test_question_template_bank(db_session, user)
        source = await create_test_question_template(
            db_session, user, question_text_template="Original text?"
        )
        await db_session.commit()

        # Link (creates copy)
        link_resp = await test_client.post(
            f"/question-template-banks/{bank.id}/question-templates/link",
            json={"question_template_id": str(source.id)},
        )
        copy_id = link_resp.json()["question_templates"][0]["id"]

        # Edit the copy independently
        await test_client.patch(
            f"/question-templates/{copy_id}",
            json={"question_text_template": "Edited in bank?"},
        )

        # Edit the source
        await test_client.patch(
            f"/question-templates/{str(source.id)}",
            json={"question_text_template": "Updated source text?"},
        )

        # Sync the copy
        response = await test_client.post(
            f"/question-template-banks/{bank.id}/question-templates/{copy_id}/sync"
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
        bank = await create_test_question_template_bank(db_session, user)
        qt = await create_test_question_template(db_session, user)
        await db_session.commit()

        await link_question_template_to_question_template_bank(
            db_session, bank.id, qt.id
        )
        await db_session.commit()

        response = await test_client.post(
            f"/question-template-banks/{bank.id}/question-templates/{qt.id}/sync"
        )

        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_sync_question_template_not_in_bank_returns_404(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test that syncing a question template not in the bank returns 404."""
        import uuid

        bank = await create_test_question_template_bank(db_session, user)
        await db_session.commit()

        response = await test_client.post(
            f"/question-template-banks/{bank.id}/question-templates/{uuid.uuid4()}/sync"
        )

        assert response.status_code == 404


@pytest.mark.integration
@pytest.mark.question_template_banks
class TestUnlinkQuestionTemplateInBank:
    """Tests for POST /question-template-banks/{id}/question-templates/{template_id}/unlink."""

    @pytest.mark.asyncio
    async def test_unlink_severs_source_reference(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test that unlink sets linked_from_template_id to null."""
        bank = await create_test_question_template_bank(db_session, user)
        source = await create_test_question_template(
            db_session, user, question_text_template="Source text?"
        )
        await db_session.commit()

        link_resp = await test_client.post(
            f"/question-template-banks/{bank.id}/question-templates/link",
            json={"question_template_id": str(source.id)},
        )
        copy_id = link_resp.json()["question_templates"][0]["id"]

        response = await test_client.post(
            f"/question-template-banks/{bank.id}/question-templates/{copy_id}/unlink"
        )

        assert response.status_code == 200
        question_templates = response.json()["question_templates"]
        copy = next(qt for qt in question_templates if qt["id"] == copy_id)
        assert copy["linked_from_template_id"] is None
        assert copy["question_text_template"] == "Source text?"

    @pytest.mark.asyncio
    async def test_unlink_question_template_not_in_bank_returns_404(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test that unlinking a question template not in the bank returns 404."""
        import uuid

        bank = await create_test_question_template_bank(db_session, user)
        await db_session.commit()

        response = await test_client.post(
            f"/question-template-banks/{bank.id}/question-templates/{uuid.uuid4()}/unlink"
        )

        assert response.status_code == 404
