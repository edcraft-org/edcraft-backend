"""Integration tests for Question Banks API endpoints."""

from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from edcraft_backend.models.user import User
from tests.factories import (
    create_test_assessment,
    create_test_folder,
    create_test_question,
    create_test_question_bank,
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


@pytest.mark.integration
@pytest.mark.question_banks
class TestSoftDeleteQuestionBank:
    """Tests for DELETE /question-banks/{bank_id} endpoint."""

    @pytest.mark.asyncio
    async def test_soft_delete_question_bank_success(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test soft deleting question bank successfully."""
        bank = await create_test_question_bank(db_session, user)
        await db_session.commit()

        response = await test_client.delete(f"/question-banks/{bank.id}")

        assert response.status_code == 204

        # Verify bank has deleted_at timestamp
        await db_session.refresh(bank)
        assert bank.deleted_at is not None

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

    @pytest.mark.asyncio
    async def test_soft_delete_question_bank_cleans_up_orphaned_questions(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test that deleting question bank triggers cleanup of orphaned questions."""
        from sqlalchemy import select

        from edcraft_backend.models.question import Question

        bank = await create_test_question_bank(db_session, user)

        orphaned_question = await create_test_question(
            db_session, user, question_text="Orphaned Question"
        )

        shared_question = await create_test_question(
            db_session, user, question_text="Shared Question"
        )
        other_bank = await create_test_question_bank(
            db_session, user, title="Other Bank"
        )
        await db_session.commit()

        # Link questions to bank
        await test_client.post(
            f"/question-banks/{bank.id}/questions/link",
            json={"question_id": str(orphaned_question.id)},
        )

        await test_client.post(
            f"/question-banks/{bank.id}/questions/link",
            json={"question_id": str(shared_question.id)},
        )
        await test_client.post(
            f"/question-banks/{other_bank.id}/questions/link",
            json={"question_id": str(shared_question.id)},
        )

        response = await test_client.delete(f"/question-banks/{bank.id}")
        assert response.status_code == 204

        orphaned_q_id = orphaned_question.id
        shared_q_id = shared_question.id

        db_session.expire_all()
        orphaned_q_result = await db_session.execute(
            select(Question).where(Question.id == orphaned_q_id)
        )
        orphaned_q = orphaned_q_result.scalar_one_or_none()
        assert orphaned_q is not None
        assert (
            orphaned_q.deleted_at is not None
        ), "Orphaned question should be soft deleted"

        shared_q_result = await db_session.execute(
            select(Question).where(Question.id == shared_q_id)
        )
        shared_q = shared_q_result.scalar_one_or_none()
        assert shared_q is not None
        assert shared_q.deleted_at is None, "Shared question should still be active"


@pytest.mark.integration
@pytest.mark.question_banks
class TestLinkQuestionToQuestionBank:
    """Tests for POST /question-banks/{bank_id}/questions/link endpoint."""

    @pytest.mark.asyncio
    async def test_link_question_to_bank_success(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test linking existing question to bank successfully."""
        bank = await create_test_question_bank(db_session, user)
        question = await create_test_question(db_session, user)
        await db_session.commit()

        link_data = {"question_id": str(question.id)}
        response = await test_client.post(
            f"/question-banks/{bank.id}/questions/link", json=link_data
        )

        assert response.status_code == 201
        data = response.json()
        assert len(data["questions"]) == 1
        assert data["questions"][0]["id"] == str(question.id)

    @pytest.mark.asyncio
    async def test_link_multiple_questions_to_bank(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test linking multiple questions to bank."""
        bank = await create_test_question_bank(db_session, user)
        question1 = await create_test_question(db_session, user)
        question2 = await create_test_question(db_session, user)
        question3 = await create_test_question(db_session, user)
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

        question_ids = [q["id"] for q in data["questions"]]
        assert str(question1.id) in question_ids
        assert str(question2.id) in question_ids
        assert str(question3.id) in question_ids

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
    async def test_link_duplicate_question_returns_error(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test linking same question twice returns error."""
        bank = await create_test_question_bank(db_session, user)
        question = await create_test_question(db_session, user)
        await db_session.commit()

        # Link question first time
        await test_client.post(
            f"/question-banks/{bank.id}/questions/link",
            json={"question_id": str(question.id)},
        )

        # Try to link same question again
        response = await test_client.post(
            f"/question-banks/{bank.id}/questions/link",
            json={"question_id": str(question.id)},
        )

        assert response.status_code == 409
        assert "already" in response.json()["detail"].lower()


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
        """Test removing question from bank successfully."""
        bank = await create_test_question_bank(db_session, user)
        question = await create_test_question(db_session, user)
        await db_session.commit()

        # Link question
        await link_question_to_question_bank(db_session, bank.id, question.id)
        await db_session.commit()

        # Remove question
        response = await test_client.delete(
            f"/question-banks/{bank.id}/questions/{question.id}"
        )

        assert response.status_code == 204

        # Verify question removed
        get_response = await test_client.get(f"/question-banks/{bank.id}")
        assert len(get_response.json()["questions"]) == 0

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

    @pytest.mark.asyncio
    async def test_remove_question_cleans_up_orphaned_question(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test that removing a question triggers cleanup if it becomes orphaned."""
        from sqlalchemy import select

        from edcraft_backend.models.question import Question

        bank = await create_test_question_bank(db_session, user)

        orphaned_question = await create_test_question(
            db_session, user, question_text="Will be orphaned"
        )

        shared_question = await create_test_question(
            db_session, user, question_text="Shared"
        )
        other_bank = await create_test_question_bank(
            db_session, user, title="Other Bank"
        )
        await db_session.commit()

        await link_question_to_question_bank(db_session, bank.id, orphaned_question.id)
        await link_question_to_question_bank(db_session, bank.id, shared_question.id)
        await link_question_to_question_bank(
            db_session, other_bank.id, shared_question.id
        )
        await db_session.commit()

        response = await test_client.delete(
            f"/question-banks/{bank.id}/questions/{orphaned_question.id}"
        )
        assert response.status_code == 204

        bank_id = bank.id
        orphaned_q_id = orphaned_question.id
        shared_q_id = shared_question.id

        db_session.expire_all()
        orphaned_q_result = await db_session.execute(
            select(Question).where(Question.id == orphaned_q_id)
        )
        orphaned_q = orphaned_q_result.scalar_one_or_none()
        assert orphaned_q is not None
        assert (
            orphaned_q.deleted_at is not None
        ), "Question should be soft deleted when orphaned"

        await test_client.delete(f"/question-banks/{bank_id}/questions/{shared_q_id}")

        db_session.expire_all()
        shared_q_result = await db_session.execute(
            select(Question).where(Question.id == shared_q_id)
        )
        shared_q = shared_q_result.scalar_one_or_none()
        assert shared_q is not None
        assert (
            shared_q.deleted_at is None
        ), "Shared question should remain active while still in use"

    @pytest.mark.asyncio
    async def test_remove_question_preserves_question_still_in_use(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test that removing question from bank doesn't delete question still used."""
        from sqlalchemy import select

        from edcraft_backend.models.question import Question

        # Create question bank and assessment
        question_bank = await create_test_question_bank(db_session, user)
        assessment = await create_test_assessment(
            db_session, user, title="Test Assessment"
        )

        # Create a question used in both question bank and assessment
        shared_question = await create_test_question(
            db_session, user, question_text="Question in both bank and assessment"
        )
        await db_session.commit()

        # Link question to both question bank and assessment
        await link_question_to_question_bank(
            db_session, question_bank.id, shared_question.id
        )
        await test_client.post(
            f"/assessments/{assessment.id}/questions/link",
            json={"question_id": str(shared_question.id)},
        )
        await db_session.commit()

        # Remove the question from the question bank
        response = await test_client.delete(
            f"/question-banks/{question_bank.id}/questions/{shared_question.id}"
        )
        assert response.status_code == 204

        # Verify the question is still active (not deleted)
        shared_q_id = shared_question.id
        db_session.expire_all()

        result = await db_session.execute(
            select(Question).where(Question.id == shared_q_id)
        )
        question = result.scalar_one_or_none()
        assert question is not None
        assert (
            question.deleted_at is None
        ), "Question should remain active when still used in assessment"
