"""Integration tests for Question Banks API endpoints."""

from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from edcraft_backend.models.enums import CollaboratorRole, ResourceType
from edcraft_backend.models.question import Question
from edcraft_backend.models.user import User
from tests.factories import (
    create_and_login_user,
    create_collaborator,
    create_test_assessment,
    create_test_folder,
    create_test_question,
    create_test_question_bank,
    create_test_user,
    link_question_to_assessment,
    link_question_to_question_bank,
)


@pytest.mark.integration
@pytest.mark.question_banks
class TestCreateQuestionBank:
    """Tests for POST /question-banks endpoint."""

    @pytest.mark.asyncio
    async def test_create_question_bank_with_folder(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test creating question bank linked to folder."""
        folder = await create_test_folder(db_session, user)
        await db_session.commit()

        bank_data = {
            "folder_id": str(folder.id),
            "title": "Python Basics Bank",
            "description": "Reusable Python questions",
        }
        response = await test_client.post("/question-banks", json=bank_data)

        assert response.status_code == 201
        data = response.json()
        assert data["folder_id"] == str(folder.id)
        assert data["title"] == "Python Basics Bank"
        assert data["description"] == "Reusable Python questions"

    @pytest.mark.asyncio
    async def test_create_question_bank_nonexistent_folder(
        self, test_client: AsyncClient, user: User
    ) -> None:
        """Test creating question bank with non-existent folder returns 404."""
        import uuid

        non_existent_folder_id = uuid.uuid4()
        bank_data = {
            "folder_id": str(non_existent_folder_id),
            "title": "Test Bank",
        }
        response = await test_client.post("/question-banks", json=bank_data)

        assert response.status_code == 404


@pytest.mark.integration
@pytest.mark.question_banks
class TestListQuestionBanks:
    """Tests for GET /question-banks endpoint."""

    @pytest.mark.asyncio
    async def test_list_question_banks_success(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test listing all question banks for a user."""
        bank1 = await create_test_question_bank(db_session, user, title="Bank 1")
        bank2 = await create_test_question_bank(db_session, user, title="Bank 2")
        await db_session.commit()

        response = await test_client.get("/question-banks")

        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 2
        bank_ids = [b["id"] for b in data]
        assert str(bank1.id) in bank_ids
        assert str(bank2.id) in bank_ids

    @pytest.mark.asyncio
    async def test_list_question_banks_filter_by_folder(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test filtering question banks by folder."""
        folder1 = await create_test_folder(db_session, user, name="Folder 1")
        folder2 = await create_test_folder(db_session, user, name="Folder 2")
        bank_in_folder1 = await create_test_question_bank(
            db_session, user, folder=folder1
        )
        await create_test_question_bank(db_session, user, folder=folder2)
        await db_session.commit()

        response = await test_client.get(
            "/question-banks",
            params={"folder_id": str(folder1.id)},
        )

        assert response.status_code == 200
        data = response.json()
        assert all(b["folder_id"] == str(folder1.id) for b in data)
        assert str(bank_in_folder1.id) in [b["id"] for b in data]

    @pytest.mark.asyncio
    async def test_list_question_banks_excludes_soft_deleted(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test that soft-deleted question banks are not in list."""
        active_bank = await create_test_question_bank(db_session, user, title="Active")
        deleted_bank = await create_test_question_bank(
            db_session, user, title="Deleted"
        )
        await db_session.commit()

        # Soft delete one bank
        await test_client.delete(f"/question-banks/{deleted_bank.id}")

        # List banks
        response = await test_client.get("/question-banks")

        assert response.status_code == 200
        data = response.json()
        bank_ids = [b["id"] for b in data]
        assert str(active_bank.id) in bank_ids
        assert str(deleted_bank.id) not in bank_ids

    @pytest.mark.asyncio
    async def test_collab_filter_owned_returns_only_owned(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """collab_filter=owned returns only banks where user is owner."""
        owned_bank = await create_test_question_bank(db_session, user)
        other_owner = await create_test_user(
            db_session, email="other_owner_qb@test.com"
        )
        shared_bank = await create_test_question_bank(db_session, other_owner)
        await db_session.commit()

        await create_collaborator(
            db_session,
            ResourceType.QUESTION_BANK,
            shared_bank.id,
            user,
            CollaboratorRole.EDITOR,
        )
        await db_session.commit()

        response = await test_client.get(
            "/question-banks", params={"collab_filter": "owned"}
        )

        assert response.status_code == 200
        ids = [b["id"] for b in response.json()]
        assert str(owned_bank.id) in ids
        assert str(shared_bank.id) not in ids

    @pytest.mark.asyncio
    async def test_collab_filter_shared_returns_only_shared(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """collab_filter=shared returns banks where user is non-owner collaborator."""
        owned_bank = await create_test_question_bank(db_session, user)
        other_owner = await create_test_user(
            db_session, email="other_owner_shared_qb@test.com"
        )
        shared_bank = await create_test_question_bank(db_session, other_owner)
        await db_session.commit()

        await create_collaborator(
            db_session,
            ResourceType.QUESTION_BANK,
            shared_bank.id,
            user,
            CollaboratorRole.VIEWER,
        )
        await db_session.commit()

        response = await test_client.get(
            "/question-banks", params={"collab_filter": "shared"}
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
        owned_bank = await create_test_question_bank(db_session, user)
        other_owner = await create_test_user(
            db_session, email="other_owner_all_qb@test.com"
        )
        shared_bank = await create_test_question_bank(db_session, other_owner)
        await db_session.commit()

        await create_collaborator(
            db_session,
            ResourceType.QUESTION_BANK,
            shared_bank.id,
            user,
            CollaboratorRole.EDITOR,
        )
        await db_session.commit()

        response = await test_client.get("/question-banks")

        assert response.status_code == 200
        ids = [b["id"] for b in response.json()]
        assert str(owned_bank.id) in ids
        assert str(shared_bank.id) in ids


@pytest.mark.integration
@pytest.mark.question_banks
class TestGetQuestionBank:
    """Tests for GET /question-banks/{bank_id} endpoint."""

    @pytest.mark.asyncio
    async def test_get_question_bank_success(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test getting a question bank successfully."""
        bank = await create_test_question_bank(db_session, user, title="Test Bank")
        await db_session.commit()

        response = await test_client.get(f"/question-banks/{bank.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(bank.id)
        assert data["title"] == "Test Bank"
        assert "questions" in data
        assert data["questions"] == []

    @pytest.mark.asyncio
    async def test_get_question_bank_with_questions(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test getting question bank includes questions (no ordering)."""
        bank = await create_test_question_bank(db_session, user)
        question1 = await create_test_question(db_session, user, question_text="Q1")
        question2 = await create_test_question(db_session, user, question_text="Q2")
        question3 = await create_test_question(db_session, user, question_text="Q3")
        await db_session.commit()

        # Link questions to bank
        await link_question_to_question_bank(db_session, bank.id, question1.id)
        await link_question_to_question_bank(db_session, bank.id, question2.id)
        await link_question_to_question_bank(db_session, bank.id, question3.id)
        await db_session.commit()

        response = await test_client.get(f"/question-banks/{bank.id}")

        assert response.status_code == 200
        data = response.json()
        assert len(data["questions"]) == 3

    @pytest.mark.asyncio
    async def test_get_question_bank_not_found(
        self, test_client: AsyncClient, user: User
    ) -> None:
        """Test getting non-existent question bank returns 404."""
        import uuid

        non_existent_id = uuid.uuid4()
        response = await test_client.get(f"/question-banks/{non_existent_id}")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_get_question_bank_soft_deleted_returns_404(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test getting soft-deleted question bank returns 404."""
        bank = await create_test_question_bank(db_session, user)
        await db_session.commit()

        # Soft delete the bank
        await test_client.delete(f"/question-banks/{bank.id}")

        # Try to get the soft-deleted bank
        response = await test_client.get(f"/question-banks/{bank.id}")

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_public_bank_by_non_owner(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test that authenticated non-collaborators can access public question banks."""
        from edcraft_backend.models.enums import ResourceVisibility

        bank = await create_test_question_bank(db_session, user, title="Public Bank")
        bank.visibility = ResourceVisibility.PUBLIC
        await db_session.commit()

        from tests.conftest import _create_test_client

        async with _create_test_client(db_session) as client2:
            _ = await create_and_login_user(
                client2, db_session, email="qb_viewer@test.com"
            )
            response = await client2.get(f"/question-banks/{bank.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(bank.id)
        assert data["visibility"] == "public"

    @pytest.mark.asyncio
    async def test_get_private_bank_by_non_owner_fails(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test that authenticated non-collaborators cannot access private question banks."""
        bank = await create_test_question_bank(db_session, user, title="Private Bank")
        await db_session.commit()

        from tests.conftest import _create_test_client

        async with _create_test_client(db_session) as client2:
            _ = await create_and_login_user(
                client2, db_session, email="qb_noviewer@test.com"
            )
            response = await client2.get(f"/question-banks/{bank.id}")

        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_get_public_bank_by_unauthenticated_user(
        self, unauth_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test that unauthenticated users can access public question banks."""
        from edcraft_backend.models.enums import ResourceVisibility

        bank = await create_test_question_bank(db_session, user, title="Public Bank")
        bank.visibility = ResourceVisibility.PUBLIC
        await db_session.commit()

        response = await unauth_client.get(f"/question-banks/{bank.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(bank.id)
        assert data["visibility"] == "public"

    @pytest.mark.asyncio
    async def test_get_private_bank_by_unauthenticated_user_fails(
        self, unauth_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test that unauthenticated users cannot access private question banks."""
        bank = await create_test_question_bank(db_session, user, title="Private Bank")
        await db_session.commit()

        response = await unauth_client.get(f"/question-banks/{bank.id}")

        assert response.status_code == 403


@pytest.mark.integration
@pytest.mark.question_banks
class TestUpdateQuestionBank:
    """Tests for PATCH /question-banks/{bank_id} endpoint."""

    @pytest.mark.asyncio
    async def test_update_question_bank_title(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test updating question bank title successfully."""
        bank = await create_test_question_bank(db_session, user, title="Old Title")
        await db_session.commit()

        update_data = {"title": "New Title"}
        response = await test_client.patch(
            f"/question-banks/{bank.id}", json=update_data
        )

        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "New Title"

    @pytest.mark.asyncio
    async def test_update_question_bank_description(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test updating question bank description successfully."""
        bank = await create_test_question_bank(
            db_session, user, description="Old description"
        )
        await db_session.commit()

        update_data = {"description": "New description"}
        response = await test_client.patch(
            f"/question-banks/{bank.id}", json=update_data
        )

        assert response.status_code == 200
        data = response.json()
        assert data["description"] == "New description"

    @pytest.mark.asyncio
    async def test_update_question_bank_move_to_folder(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test moving question bank to different folder."""
        folder1 = await create_test_folder(db_session, user, name="Folder 1")
        folder2 = await create_test_folder(db_session, user, name="Folder 2")
        bank = await create_test_question_bank(db_session, user, folder=folder1)
        await db_session.commit()

        update_data = {"folder_id": str(folder2.id)}
        response = await test_client.patch(
            f"/question-banks/{bank.id}", json=update_data
        )

        assert response.status_code == 200
        data = response.json()
        assert data["folder_id"] == str(folder2.id)

    @pytest.mark.asyncio
    async def test_update_question_bank_not_found(
        self, test_client: AsyncClient, user: User
    ) -> None:
        """Test updating non-existent question bank returns 404."""
        import uuid

        non_existent_id = uuid.uuid4()
        update_data = {"title": "New Title"}
        response = await test_client.patch(
            f"/question-banks/{non_existent_id}", json=update_data
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_question_bank_visibility(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test that owner can update question bank visibility."""
        bank = await create_test_question_bank(db_session, user)
        await db_session.commit()

        response = await test_client.patch(
            f"/question-banks/{bank.id}", json={"visibility": "public"}
        )

        assert response.status_code == 200
        assert response.json()["visibility"] == "public"

    @pytest.mark.asyncio
    async def test_editor_can_update_question_bank(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test that an editor collaborator can PATCH the question bank."""
        other_user = await create_test_user(
            db_session, email="qb_owner_edit@test.com"
        )
        bank = await create_test_question_bank(
            db_session, other_user, title="Original Title"
        )
        await db_session.commit()

        await create_collaborator(
            db_session,
            ResourceType.QUESTION_BANK,
            bank.id,
            user,
            CollaboratorRole.EDITOR,
        )
        await db_session.commit()

        response = await test_client.patch(
            f"/question-banks/{bank.id}", json={"title": "Updated By Editor"}
        )

        assert response.status_code == 200
        assert response.json()["title"] == "Updated By Editor"

    @pytest.mark.asyncio
    async def test_viewer_cannot_update_question_bank_returns_403(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test that a viewer collaborator cannot PATCH the question bank (403)."""
        other_user = await create_test_user(
            db_session, email="qb_owner_viewer@test.com"
        )
        bank = await create_test_question_bank(
            db_session, other_user, title="Original Title"
        )
        await db_session.commit()

        await create_collaborator(
            db_session,
            ResourceType.QUESTION_BANK,
            bank.id,
            user,
            CollaboratorRole.VIEWER,
        )
        await db_session.commit()

        response = await test_client.patch(
            f"/question-banks/{bank.id}", json={"title": "Should Fail"}
        )

        assert response.status_code == 403


@pytest.mark.integration
@pytest.mark.question_banks
class TestSoftDeleteQuestionBank:
    """Tests for DELETE /question-banks/{bank_id} endpoint."""

    @pytest.mark.asyncio
    async def test_soft_delete_question_bank_success(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test soft deleting question bank and its questions."""
        bank = await create_test_question_bank(db_session, user)
        question = await create_test_question(db_session, user)
        await link_question_to_question_bank(db_session, bank.id, question.id)
        await db_session.commit()

        question_id = question.id

        response = await test_client.delete(f"/question-banks/{bank.id}")

        assert response.status_code == 204

        # Verify bank has deleted_at timestamp
        await db_session.refresh(bank)
        assert bank.deleted_at is not None

        # Verify the question is soft-deleted with the bank
        db_session.expire_all()
        deleted_question = (
            await db_session.execute(select(Question).where(Question.id == question_id))
        ).scalar_one_or_none()
        assert deleted_question is not None
        assert deleted_question.deleted_at is not None

    @pytest.mark.asyncio
    async def test_soft_delete_question_bank_not_in_list(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test soft-deleted question bank not in list results."""
        bank = await create_test_question_bank(db_session, user)
        await db_session.commit()

        # Soft delete bank
        await test_client.delete(f"/question-banks/{bank.id}")

        # List banks
        response = await test_client.get("/question-banks")

        assert response.status_code == 200
        data = response.json()
        bank_ids = [b["id"] for b in data]
        assert str(bank.id) not in bank_ids

    @pytest.mark.asyncio
    async def test_soft_delete_question_bank_not_found(
        self, test_client: AsyncClient, user: User
    ) -> None:
        """Test soft deleting non-existent question bank returns 404."""
        import uuid

        non_existent_id = uuid.uuid4()
        response = await test_client.delete(f"/question-banks/{non_existent_id}")

        assert response.status_code == 404


@pytest.mark.integration
@pytest.mark.question_banks
class TestLinkQuestionToQuestionBank:
    """Tests for POST /question-banks/{bank_id}/questions/link endpoint."""

    @pytest.mark.asyncio
    async def test_link_question_to_bank_success(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test linking creates an independent copy with source reference."""
        bank = await create_test_question_bank(db_session, user)
        question = await create_test_question(
            db_session, user, question_text="Source Q"
        )
        await db_session.commit()

        link_data = {"question_id": str(question.id)}
        response = await test_client.post(
            f"/question-banks/{bank.id}/questions/link", json=link_data
        )

        assert response.status_code == 201
        data = response.json()
        assert len(data["questions"]) == 1
        copy = data["questions"][0]
        assert copy["id"] != str(question.id)
        assert copy["linked_from_question_id"] == str(question.id)
        assert copy["question_text"] == "Source Q"

    @pytest.mark.asyncio
    async def test_link_multiple_questions_to_bank(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test linking multiple questions to bank."""
        bank = await create_test_question_bank(db_session, user)
        question1 = await create_test_question(db_session, user, question_text="Q1")
        question2 = await create_test_question(db_session, user, question_text="Q2")
        question3 = await create_test_question(db_session, user, question_text="Q3")
        await db_session.commit()

        # Link questions
        await test_client.post(
            f"/question-banks/{bank.id}/questions/link",
            json={"question_id": str(question1.id)},
        )
        await test_client.post(
            f"/question-banks/{bank.id}/questions/link",
            json={"question_id": str(question2.id)},
        )
        response = await test_client.post(
            f"/question-banks/{bank.id}/questions/link",
            json={"question_id": str(question3.id)},
        )

        assert response.status_code == 201
        data = response.json()
        assert len(data["questions"]) == 3

        source_links = {q["linked_from_question_id"] for q in data["questions"]}
        assert str(question1.id) in source_links
        assert str(question2.id) in source_links
        assert str(question3.id) in source_links

    @pytest.mark.asyncio
    async def test_link_question_to_nonexistent_bank(
        self, test_client: AsyncClient, user: User
    ) -> None:
        """Test linking question to non-existent bank returns 404."""
        import uuid

        non_existent_bank_id = uuid.uuid4()
        link_data = {"question_id": str(uuid.uuid4())}
        response = await test_client.post(
            f"/question-banks/{non_existent_bank_id}/questions/link",
            json=link_data,
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_link_nonexistent_question_to_bank(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test linking non-existent question to bank returns 404."""
        import uuid

        bank = await create_test_question_bank(db_session, user)
        await db_session.commit()

        non_existent_question_id = uuid.uuid4()
        link_data = {"question_id": str(non_existent_question_id)}
        response = await test_client.post(
            f"/question-banks/{bank.id}/questions/link", json=link_data
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_link_same_source_twice_creates_two_copies(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test linking the same source question twice creates two independent copies."""
        bank = await create_test_question_bank(db_session, user)
        question = await create_test_question(db_session, user)
        await db_session.commit()

        await test_client.post(
            f"/question-banks/{bank.id}/questions/link",
            json={"question_id": str(question.id)},
        )
        response = await test_client.post(
            f"/question-banks/{bank.id}/questions/link",
            json={"question_id": str(question.id)},
        )

        assert response.status_code == 201
        data = response.json()
        assert len(data["questions"]) == 2
        ids = [q["id"] for q in data["questions"]]
        assert ids[0] != ids[1]
        assert all(
            q["linked_from_question_id"] == str(question.id) for q in data["questions"]
        )

    @pytest.mark.asyncio
    async def test_link_question_from_other_assessment_as_viewer(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test that a viewer on a source assessment can link its questions to a bank."""
        owner2 = await create_test_user(db_session)
        assessment = await create_test_assessment(db_session, owner2)
        source_question = await create_test_question(
            db_session, owner2, question_text="Source Q"
        )
        await link_question_to_assessment(db_session, assessment.id, source_question.id)

        await create_collaborator(
            db_session,
            ResourceType.ASSESSMENT,
            assessment.id,
            user,
            CollaboratorRole.VIEWER,
        )
        dest_bank = await create_test_question_bank(db_session, user)
        await db_session.commit()

        response = await test_client.post(
            f"/question-banks/{dest_bank.id}/questions/link",
            json={"question_id": str(source_question.id)},
        )

        assert response.status_code == 201
        data = response.json()
        assert len(data["questions"]) == 1
        assert data["questions"][0]["linked_from_question_id"] == str(source_question.id)
        assert data["questions"][0]["question_text"] == "Source Q"

    @pytest.mark.asyncio
    async def test_link_question_without_access_returns_403(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test that linking a question without access returns 403."""
        owner2 = await create_test_user(db_session)
        private_assessment = await create_test_assessment(db_session, owner2)
        private_question = await create_test_question(db_session, owner2)
        await link_question_to_assessment(
            db_session, private_assessment.id, private_question.id
        )
        dest_bank = await create_test_question_bank(db_session, user)
        await db_session.commit()

        response = await test_client.post(
            f"/question-banks/{dest_bank.id}/questions/link",
            json={"question_id": str(private_question.id)},
        )

        assert response.status_code == 403


@pytest.mark.integration
@pytest.mark.question_banks
class TestSyncQuestionInQuestionBank:
    """Tests for POST /question-banks/{question_bank_id}/questions/{question_id}/sync."""

    @pytest.mark.asyncio
    async def test_sync_updates_copy_from_source(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test that sync overwrites copy content with the current source content."""
        bank = await create_test_question_bank(db_session, user)
        source = await create_test_question(
            db_session, user, question_text="Original text"
        )
        await db_session.commit()

        # Link (creates copy)
        link_resp = await test_client.post(
            f"/question-banks/{bank.id}/questions/link",
            json={"question_id": str(source.id)},
        )
        copy_id = link_resp.json()["questions"][0]["id"]

        # Edit the source
        await test_client.patch(
            f"/questions/{str(source.id)}",
            json={"question_text": "Updated source text"},
        )

        # Sync the copy
        response = await test_client.post(
            f"/question-banks/{bank.id}/questions/{copy_id}/sync"
        )

        assert response.status_code == 200
        questions = response.json()["questions"]
        copy = next(q for q in questions if q["id"] == copy_id)
        assert copy["question_text"] == "Updated source text"
        assert copy["linked_from_question_id"] == str(source.id)

    @pytest.mark.asyncio
    async def test_sync_without_source_link_returns_400(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test that syncing a question with no source link returns 400."""
        bank = await create_test_question_bank(db_session, user)
        question = await create_test_question(db_session, user)
        await link_question_to_question_bank(db_session, bank.id, question.id)
        await db_session.commit()

        response = await test_client.post(
            f"/question-banks/{bank.id}/questions/{question.id}/sync"
        )

        assert response.status_code == 400


@pytest.mark.integration
@pytest.mark.question_banks
class TestUnlinkQuestionInQuestionBank:
    """Tests for POST /question-banks/{question_bank_id}/questions/{question_id}/unlink."""

    @pytest.mark.asyncio
    async def test_unlink_severs_source_reference(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test that unlink sets linked_from_question_id to null while keeping the question."""
        bank = await create_test_question_bank(db_session, user)
        source = await create_test_question(db_session, user, question_text="Source")
        await db_session.commit()

        link_resp = await test_client.post(
            f"/question-banks/{bank.id}/questions/link",
            json={"question_id": str(source.id)},
        )
        copy_id = link_resp.json()["questions"][0]["id"]

        response = await test_client.post(
            f"/question-banks/{bank.id}/questions/{copy_id}/unlink"
        )

        assert response.status_code == 200
        questions = response.json()["questions"]
        copy = next(q for q in questions if q["id"] == copy_id)
        assert copy["linked_from_question_id"] is None
        assert copy["question_text"] == "Source"


@pytest.mark.integration
@pytest.mark.question_banks
class TestInsertQuestionToQuestionBank:
    """Tests for POST /question-banks/{bank_id}/questions endpoint."""

    @pytest.mark.asyncio
    async def test_insert_question_to_bank_success(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test inserting a new question to bank successfully."""
        bank = await create_test_question_bank(db_session, user)
        await db_session.commit()

        question_data: dict[str, Any] = {
            "question": {
                "question_type": "mcq",
                "question_text": "What is 2+2?",
                "data": {
                    "options": ["3", "4", "5", "6"],
                    "correct_index": 1,
                },
            }
        }
        response = await test_client.post(
            f"/question-banks/{bank.id}/questions", json=question_data
        )

        assert response.status_code == 201
        data = response.json()
        assert len(data["questions"]) == 1
        assert data["questions"][0]["question_text"] == "What is 2+2?"
        assert data["questions"][0]["question_type"] == "mcq"

    @pytest.mark.asyncio
    async def test_insert_multiple_questions_to_bank(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test inserting multiple questions to bank."""
        bank = await create_test_question_bank(db_session, user)
        await db_session.commit()

        # Add first question
        question1_data: dict[str, Any] = {
            "question": {
                "question_type": "short_answer",
                "question_text": "What is Python?",
                "data": {"correct_answer": "A programming language"},
            }
        }
        await test_client.post(
            f"/question-banks/{bank.id}/questions", json=question1_data
        )

        # Add second question
        question2_data: dict[str, Any] = {
            "question": {
                "question_type": "mrq",
                "question_text": "Select all data types:",
                "data": {
                    "options": ["int", "str", "bool", "float"],
                    "correct_indices": [0, 1, 2, 3],
                },
            }
        }
        response = await test_client.post(
            f"/question-banks/{bank.id}/questions", json=question2_data
        )

        assert response.status_code == 201
        data = response.json()
        assert len(data["questions"]) == 2

    @pytest.mark.asyncio
    async def test_insert_question_to_nonexistent_bank(
        self, test_client: AsyncClient, user: User
    ) -> None:
        """Test inserting question to non-existent bank returns 404."""
        import uuid

        non_existent_bank_id = uuid.uuid4()
        question_data: dict[str, Any] = {
            "question": {
                "question_type": "short_answer",
                "question_text": "Test question",
                "data": {"correct_answer": "answer"},
            }
        }
        response = await test_client.post(
            f"/question-banks/{non_existent_bank_id}/questions", json=question_data
        )

        assert response.status_code == 404


@pytest.mark.integration
@pytest.mark.question_banks
class TestRemoveQuestionFromQuestionBank:
    """Tests for DELETE /question-banks/{bank_id}/questions/{question_id} endpoint."""

    @pytest.mark.asyncio
    async def test_remove_question_from_bank_success(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test removing question from bank removes it and soft-deletes it."""
        bank = await create_test_question_bank(db_session, user)
        question = await create_test_question(db_session, user)
        await link_question_to_question_bank(db_session, bank.id, question.id)
        await db_session.commit()

        question_id = question.id

        response = await test_client.delete(
            f"/question-banks/{bank.id}/questions/{question_id}"
        )

        assert response.status_code == 204

        # Verify question removed from bank
        get_response = await test_client.get(f"/question-banks/{bank.id}")
        assert len(get_response.json()["questions"]) == 0

        # Verify question is soft-deleted
        db_session.expire_all()
        deleted_question = (
            await db_session.execute(select(Question).where(Question.id == question_id))
        ).scalar_one_or_none()
        assert deleted_question is not None
        assert deleted_question.deleted_at is not None

    @pytest.mark.asyncio
    async def test_remove_question_preserves_other_questions(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test removing one question preserves other questions."""
        bank = await create_test_question_bank(db_session, user)
        question1 = await create_test_question(db_session, user)
        question2 = await create_test_question(db_session, user)
        await db_session.commit()

        # Link both questions
        await link_question_to_question_bank(db_session, bank.id, question1.id)
        await link_question_to_question_bank(db_session, bank.id, question2.id)
        await db_session.commit()

        # Remove first question
        await test_client.delete(f"/question-banks/{bank.id}/questions/{question1.id}")

        # Verify only second question remains
        response = await test_client.get(f"/question-banks/{bank.id}")
        data = response.json()
        assert len(data["questions"]) == 1
        assert data["questions"][0]["id"] == str(question2.id)

    @pytest.mark.asyncio
    async def test_remove_question_from_nonexistent_bank(
        self, test_client: AsyncClient, user: User
    ) -> None:
        """Test removing question from non-existent bank returns 404."""
        import uuid

        non_existent_bank_id = uuid.uuid4()
        question_id = uuid.uuid4()
        response = await test_client.delete(
            f"/question-banks/{non_existent_bank_id}/questions/{question_id}"
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_remove_nonexistent_question_from_bank(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test removing non-existent question from bank returns 404."""
        import uuid

        bank = await create_test_question_bank(db_session, user)
        await db_session.commit()

        non_existent_question_id = uuid.uuid4()
        response = await test_client.delete(
            f"/question-banks/{bank.id}/questions/{non_existent_question_id}"
        )

        assert response.status_code == 404
