"""Integration tests for Questions API endpoints."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from edcraft_backend.models.assessment_question import AssessmentQuestion
from edcraft_backend.repositories.assessment_question_repository import (
    AssessmentQuestionRepository,
)
from tests.factories import (
    create_test_assessment,
    create_test_question,
    create_test_question_template,
    create_test_user,
)


@pytest.mark.integration
@pytest.mark.questions
class TestListQuestions:
    """Tests for GET /questions endpoint."""

    @pytest.mark.asyncio
    async def test_list_questions_success(
        self, test_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test listing all questions for a user."""
        user = await create_test_user(db_session)
        question1 = await create_test_question(
            db_session, user, question_type="mcq"
        )
        question2 = await create_test_question(
            db_session, user, question_type="mrq"
        )
        await db_session.commit()

        response = await test_client.get("/questions", params={"owner_id": str(user.id)})

        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 2
        question_ids = [q["id"] for q in data]
        assert str(question1.id) in question_ids
        assert str(question2.id) in question_ids

    @pytest.mark.asyncio
    async def test_list_questions_excludes_soft_deleted(
        self, test_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test that soft-deleted questions are not in list."""
        user = await create_test_user(db_session)
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
        response = await test_client.get("/questions", params={"owner_id": str(user.id)})

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
        self, test_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test getting a question successfully."""
        user = await create_test_user(db_session)
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
        self, test_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test getting question includes template relationship if exists."""
        user = await create_test_user(db_session)
        template = await create_test_question_template(db_session, user)
        question = await create_test_question(db_session, user, template=template)
        await db_session.commit()

        response = await test_client.get(f"/questions/{question.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["template_id"] == str(template.id)

    @pytest.mark.asyncio
    async def test_get_question_not_found(self, test_client: AsyncClient) -> None:
        """Test getting non-existent question returns 404."""
        import uuid

        non_existent_id = uuid.uuid4()
        response = await test_client.get(f"/questions/{non_existent_id}")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_get_question_soft_deleted_returns_404(
        self, test_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test getting soft-deleted question returns 404."""
        user = await create_test_user(db_session)
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
        self, test_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test updating question text successfully."""
        user = await create_test_user(db_session)
        question = await create_test_question(
            db_session, user, question_text="Old text"
        )
        await db_session.commit()

        update_data = {"question_text": "New text"}
        response = await test_client.patch(f"/questions/{question.id}", json=update_data)

        assert response.status_code == 200
        data = response.json()
        assert data["question_text"] == "New text"

    @pytest.mark.asyncio
    async def test_update_question_options(
        self, test_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test updating question options successfully."""
        user = await create_test_user(db_session)
        question = await create_test_question(
            db_session,
            user,
            additional_data={"options": ["A", "B"], "correct_indices": [0]},
        )
        await db_session.commit()

        update_data = {
            "additional_data": {
                "options": ["X", "Y", "Z"],
                "correct_indices": ["1", "2"],
            }
        }
        response = await test_client.patch(f"/questions/{question.id}", json=update_data)

        assert response.status_code == 200
        data = response.json()
        assert data["additional_data"]["options"] == ["X", "Y", "Z"]
        assert data["additional_data"]["correct_indices"] == ["1", "2"]

    @pytest.mark.asyncio
    async def test_update_question_correct_indices(
        self, test_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test updating correct_indices successfully."""
        user = await create_test_user(db_session)
        question = await create_test_question(
            db_session,
            user,
            additional_data={
                "options": ["A", "B", "C", "D"],
                "correct_indices": [0],
            },
        )
        await db_session.commit()

        update_data = {"additional_data": {"correct_indices": [2]}}
        response = await test_client.patch(f"/questions/{question.id}", json=update_data)

        assert response.status_code == 200
        data = response.json()
        assert data["additional_data"]["correct_indices"] == [2]

    @pytest.mark.asyncio
    async def test_update_question_not_found(self, test_client: AsyncClient) -> None:
        """Test updating non-existent question returns 404."""
        import uuid

        non_existent_id = uuid.uuid4()
        update_data = {"question_text": "New text"}
        response = await test_client.patch(f"/questions/{non_existent_id}", json=update_data)

        assert response.status_code == 404


@pytest.mark.integration
@pytest.mark.questions
class TestSoftDeleteQuestion:
    """Tests for DELETE /questions/{question_id} endpoint."""

    @pytest.mark.asyncio
    async def test_soft_delete_question_success(
        self, test_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test soft deleting question successfully."""
        user = await create_test_user(db_session)
        question = await create_test_question(db_session, user)
        await db_session.commit()

        response = await test_client.delete(f"/questions/{question.id}")

        assert response.status_code == 204

        # Verify question has deleted_at timestamp
        await db_session.refresh(question)
        assert question.deleted_at is not None

    @pytest.mark.asyncio
    async def test_soft_delete_question_not_in_list(
        self, test_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test soft-deleted question not in list results."""
        user = await create_test_user(db_session)
        question = await create_test_question(db_session, user)
        await db_session.commit()

        # Soft delete question
        await test_client.delete(f"/questions/{question.id}")

        # List questions
        response = await test_client.get("/questions", params={"owner_id": str(user.id)})

        assert response.status_code == 200
        data = response.json()
        question_ids = [q["id"] for q in data]
        assert str(question.id) not in question_ids

    @pytest.mark.asyncio
    async def test_soft_delete_preserves_template_reference(
        self, test_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test soft deleting question preserves template_id reference."""
        user = await create_test_user(db_session)
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
    async def test_soft_delete_question_not_found(self, test_client: AsyncClient) -> None:
        """Test soft deleting non-existent question returns 404."""
        import uuid

        non_existent_id = uuid.uuid4()
        response = await test_client.delete(f"/questions/{non_existent_id}")

        assert response.status_code == 404


@pytest.mark.integration
@pytest.mark.questions
class TestGetAssessmentsForQuestion:
    """Tests for GET /questions/{question_id}/assessments endpoint."""

    @pytest.mark.asyncio
    async def test_get_assessments_for_question_success(
        self, test_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test getting assessments that include a question."""
        user = await create_test_user(db_session)
        question = await create_test_question(db_session, user)
        assessment1 = await create_test_assessment(
            db_session, user, title="Assessment 1"
        )
        assessment2 = await create_test_assessment(
            db_session, user, title="Assessment 2"
        )
        await db_session.commit()

        # Link question to both assessments
        assoc_repo = AssessmentQuestionRepository(db_session)
        assoc1 = AssessmentQuestion(
            assessment_id=assessment1.id, question_id=question.id, order=0
        )
        assoc2 = AssessmentQuestion(
            assessment_id=assessment2.id, question_id=question.id, order=0
        )
        await assoc_repo.create(assoc1)
        await assoc_repo.create(assoc2)
        await db_session.commit()

        # Get assessments for question
        response = await test_client.get(
            f"/questions/{question.id}/assessments",
            params={"owner_id": str(user.id)},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assessment_ids = [a["id"] for a in data]
        assert str(assessment1.id) in assessment_ids
        assert str(assessment2.id) in assessment_ids
        assert "title" in data[0]

    @pytest.mark.asyncio
    async def test_get_assessments_for_question_unauthorized(
        self, test_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test accessing assessments for question not owned by user."""
        user1 = await create_test_user(db_session, email="user1@test.com")
        user2 = await create_test_user(db_session, email="user2@test.com")
        question = await create_test_question(db_session, user1)
        await db_session.commit()

        response = await test_client.get(
            f"/questions/{question.id}/assessments",
            params={"owner_id": str(user2.id)},
        )

        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_get_assessments_for_question_not_found(
        self, test_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test getting assessments for non-existent question."""
        import uuid

        user = await create_test_user(db_session)
        await db_session.commit()

        non_existent_id = uuid.uuid4()
        response = await test_client.get(
            f"/questions/{non_existent_id}/assessments",
            params={"owner_id": str(user.id)},
        )

        assert response.status_code == 404
