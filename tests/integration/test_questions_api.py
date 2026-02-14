"""Integration tests for Questions API endpoints."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from edcraft_backend.models.user import User
from tests.factories import (
    create_test_assessment,
    create_test_question,
    create_test_question_bank,
    create_test_question_template,
    create_test_user,
    link_question_to_assessment,
    link_question_to_question_bank,
)


@pytest.mark.integration
@pytest.mark.questions
class TestListQuestions:
    """Tests for GET /questions endpoint."""

    @pytest.mark.asyncio
    async def test_list_questions_success(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test listing all questions for a user."""
        question1 = await create_test_question(db_session, user, question_type="mcq")
        question2 = await create_test_question(db_session, user, question_type="mrq")
        await db_session.commit()

        response = await test_client.get("/questions")

        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 2
        question_ids = [q["id"] for q in data]
        assert str(question1.id) in question_ids
        assert str(question2.id) in question_ids

    @pytest.mark.asyncio
    async def test_list_questions_excludes_soft_deleted(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test that soft-deleted questions are not in list."""
        active_question = await create_test_question(
            db_session, user, question_text="Active question"
        )
        deleted_question = await create_test_question(
            db_session, user, question_text="Deleted question"
        )
        await db_session.commit()

        # Soft delete one question
        await test_client.delete(f"/questions/{deleted_question.id}")

        # List questions
        response = await test_client.get("/questions")

        assert response.status_code == 200
        data = response.json()
        question_ids = [q["id"] for q in data]
        assert str(active_question.id) in question_ids
        assert str(deleted_question.id) not in question_ids


@pytest.mark.integration
@pytest.mark.questions
class TestGetQuestion:
    """Tests for GET /questions/{question_id} endpoint."""

    @pytest.mark.asyncio
    async def test_get_question_success(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test getting a question successfully."""
        question = await create_test_question(
            db_session,
            user,
            question_type="mcq",
            question_text="Test question?",
        )
        await db_session.commit()

        response = await test_client.get(f"/questions/{question.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(question.id)
        assert data["question_type"] == "mcq"
        assert data["question_text"] == "Test question?"

    @pytest.mark.asyncio
    async def test_get_question_includes_template_relationship(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test getting question includes template relationship if exists."""
        template = await create_test_question_template(db_session, user)
        question = await create_test_question(db_session, user, template=template)
        await db_session.commit()

        response = await test_client.get(f"/questions/{question.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["template_id"] == str(template.id)

    @pytest.mark.asyncio
    async def test_get_question_not_found(
        self, test_client: AsyncClient, user: User
    ) -> None:
        """Test getting non-existent question returns 404."""
        import uuid

        non_existent_id = uuid.uuid4()
        response = await test_client.get(f"/questions/{non_existent_id}")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_get_question_soft_deleted_returns_404(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test getting soft-deleted question returns 404."""
        question = await create_test_question(db_session, user)
        await db_session.commit()

        # Soft delete the question
        await test_client.delete(f"/questions/{question.id}")

        # Try to get the soft-deleted question
        response = await test_client.get(f"/questions/{question.id}")

        assert response.status_code == 404


@pytest.mark.integration
@pytest.mark.questions
class TestUpdateQuestion:
    """Tests for PATCH /questions/{question_id} endpoint."""

    @pytest.mark.asyncio
    async def test_update_question_text(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test updating question text successfully."""
        question = await create_test_question(
            db_session, user, question_text="Old text"
        )
        await db_session.commit()

        update_data = {"question_text": "New text"}
        response = await test_client.patch(
            f"/questions/{question.id}", json=update_data
        )

        assert response.status_code == 200
        data = response.json()
        assert data["question_text"] == "New text"

    @pytest.mark.asyncio
    async def test_update_question_options(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test updating question options successfully."""
        question = await create_test_question(
            db_session,
            user,
            question_type="mrq",
            options=["A", "B"],
            correct_indices=[0],
        )
        await db_session.commit()

        update_data = {
            "data": {
                "options": ["X", "Y", "Z"],
                "correct_indices": [1, 2],
            }
        }
        response = await test_client.patch(
            f"/questions/{question.id}", json=update_data
        )

        assert response.status_code == 200
        data = response.json()
        assert data["mrq_data"]["options"] == ["X", "Y", "Z"]
        assert data["mrq_data"]["correct_indices"] == [1, 2]

    @pytest.mark.asyncio
    async def test_update_question_correct_index(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test updating correct_index successfully."""
        question = await create_test_question(
            db_session,
            user,
            question_type="mcq",
            options=["A", "B", "C", "D"],
            correct_index=0,
        )
        await db_session.commit()

        update_data = {"data": {"options": ["A", "B", "C", "D"], "correct_index": 2}}
        response = await test_client.patch(
            f"/questions/{question.id}", json=update_data
        )

        assert response.status_code == 200
        data = response.json()
        assert data["mcq_data"]["correct_index"] == 2

    @pytest.mark.asyncio
    async def test_update_question_type(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test changing question type from MCQ to MRQ."""
        question = await create_test_question(
            db_session,
            user,
            question_type="mcq",
            question_text="Original MCQ question?",
            options=["A", "B", "C"],
            correct_index=0,
        )
        await db_session.commit()

        update_data = {
            "question_type": "mrq",
            "question_text": "Updated MRQ question?",
            "data": {
                "options": ["X", "Y", "Z"],
                "correct_indices": [0, 2],
            },
        }
        response = await test_client.patch(
            f"/questions/{question.id}", json=update_data
        )

        assert response.status_code == 200
        data = response.json()
        assert data["question_type"] == "mrq"
        assert data["question_text"] == "Updated MRQ question?"
        assert data["mrq_data"]["options"] == ["X", "Y", "Z"]
        assert data["mrq_data"]["correct_indices"] == [0, 2]
        assert "mcq_data" not in data

    @pytest.mark.asyncio
    async def test_update_question_not_found(
        self, test_client: AsyncClient, user: User
    ) -> None:
        """Test updating non-existent question returns 404."""
        import uuid

        non_existent_id = uuid.uuid4()
        update_data = {"question_text": "New text"}
        response = await test_client.patch(
            f"/questions/{non_existent_id}", json=update_data
        )

        assert response.status_code == 404


@pytest.mark.integration
@pytest.mark.questions
class TestSoftDeleteQuestion:
    """Tests for DELETE /questions/{question_id} endpoint."""

    @pytest.mark.asyncio
    async def test_soft_delete_question_success(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test soft deleting question successfully."""
        question = await create_test_question(db_session, user)
        await db_session.commit()

        response = await test_client.delete(f"/questions/{question.id}")

        assert response.status_code == 204

        # Verify question has deleted_at timestamp
        await db_session.refresh(question)
        assert question.deleted_at is not None

    @pytest.mark.asyncio
    async def test_soft_delete_question_not_in_list(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test soft-deleted question not in list results."""
        question = await create_test_question(db_session, user)
        await db_session.commit()

        # Soft delete question
        await test_client.delete(f"/questions/{question.id}")

        # List questions
        response = await test_client.get("/questions")

        assert response.status_code == 200
        data = response.json()
        question_ids = [q["id"] for q in data]
        assert str(question.id) not in question_ids

    @pytest.mark.asyncio
    async def test_soft_delete_preserves_template_reference(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test soft deleting question preserves template_id reference."""
        template = await create_test_question_template(db_session, user)
        question = await create_test_question(db_session, user, template=template)
        await db_session.commit()

        # Soft delete question
        await test_client.delete(f"/questions/{question.id}")

        # Verify template reference still exists in database
        await db_session.refresh(question)
        assert question.template_id == template.id
        assert question.deleted_at is not None

    @pytest.mark.asyncio
    async def test_soft_delete_question_not_found(
        self, test_client: AsyncClient, user: User
    ) -> None:
        """Test soft deleting non-existent question returns 404."""
        import uuid

        non_existent_id = uuid.uuid4()
        response = await test_client.delete(f"/questions/{non_existent_id}")

        assert response.status_code == 404


@pytest.mark.integration
@pytest.mark.questions
class TestGetUsageForQuestion:
    """Tests for GET /questions/{question_id}/usage endpoint."""

    @pytest.mark.asyncio
    async def test_get_question_usage_success(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test getting question usage returns both assessments and banks."""
        question = await create_test_question(db_session, user)
        assessment = await create_test_assessment(
            db_session, user, title="Test Assessment"
        )
        question_bank = await create_test_question_bank(
            db_session, user, title="Test Bank"
        )
        await db_session.commit()

        await link_question_to_assessment(db_session, assessment.id, question.id)
        await link_question_to_question_bank(db_session, question_bank.id, question.id)
        await db_session.commit()

        response = await test_client.get(f"/questions/{question.id}/usage")

        assert response.status_code == 200
        data = response.json()

        assert "assessments" in data
        assert "question_banks" in data

        assert len(data["assessments"]) == 1
        assert len(data["question_banks"]) == 1
        assert data["assessments"][0]["id"] == str(assessment.id)
        assert data["question_banks"][0]["id"] == str(question_bank.id)

    @pytest.mark.asyncio
    async def test_get_question_usage_unauthorized(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test accessing question usage for question not owned by current user."""
        other_user = await create_test_user(db_session, email="other@test.com")
        question = await create_test_question(db_session, other_user)
        await db_session.commit()

        response = await test_client.get(f"/questions/{question.id}/usage")

        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_get_question_usage_not_found(
        self, test_client: AsyncClient, user: User
    ) -> None:
        """Test getting question usage for non-existent question."""
        import uuid

        non_existent_id = uuid.uuid4()
        response = await test_client.get(f"/questions/{non_existent_id}/usage")

        assert response.status_code == 404
