"""Integration tests for Assessments API endpoints."""

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
    link_question_to_assessment,
    link_question_to_question_bank,
)


@pytest.mark.integration
@pytest.mark.assessments
class TestCreateAssessment:
    """Tests for POST /assessments endpoint."""

    @pytest.mark.asyncio
    async def test_create_assessment_with_folder(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test creating assessment linked to folder."""
        folder = await create_test_folder(db_session, user)
        await db_session.commit()

        assessment_data = {
            "folder_id": str(folder.id),
            "title": "Assessment in Folder",
            "description": "Test description",
        }
        response = await test_client.post("/assessments", json=assessment_data)

        assert response.status_code == 201
        data = response.json()
        assert data["folder_id"] == str(folder.id)

    @pytest.mark.asyncio
    async def test_create_assessment_nonexistent_folder(
        self, test_client: AsyncClient, user: User
    ) -> None:
        """Test creating assessment with non-existent folder returns 404."""
        import uuid

        non_existent_folder_id = uuid.uuid4()
        assessment_data = {
            "folder_id": str(non_existent_folder_id),
            "title": "Test Assessment",
        }
        response = await test_client.post("/assessments", json=assessment_data)

        assert response.status_code == 404


@pytest.mark.integration
@pytest.mark.assessments
class TestListAssessments:
    """Tests for GET /assessments endpoint."""

    @pytest.mark.asyncio
    async def test_list_assessments_success(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test listing all assessments for a user."""
        assessment1 = await create_test_assessment(
            db_session, user, title="Assessment 1"
        )
        assessment2 = await create_test_assessment(
            db_session, user, title="Assessment 2"
        )
        await db_session.commit()

        response = await test_client.get("/assessments")

        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 2
        assessment_ids = [a["id"] for a in data]
        assert str(assessment1.id) in assessment_ids
        assert str(assessment2.id) in assessment_ids

    @pytest.mark.asyncio
    async def test_list_assessments_filter_by_folder(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test filtering assessments by folder."""
        folder1 = await create_test_folder(db_session, user, name="Folder 1")
        folder2 = await create_test_folder(db_session, user, name="Folder 2")
        assessment_in_folder1 = await create_test_assessment(
            db_session, user, folder=folder1
        )
        await create_test_assessment(db_session, user, folder=folder2)
        await db_session.commit()

        response = await test_client.get(
            "/assessments",
            params={"folder_id": str(folder1.id)},
        )

        assert response.status_code == 200
        data = response.json()
        assert all(a["folder_id"] == str(folder1.id) for a in data)
        assert str(assessment_in_folder1.id) in [a["id"] for a in data]

    @pytest.mark.asyncio
    async def test_list_assessments_excludes_soft_deleted(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test that soft-deleted assessments are not in list."""
        active_assessment = await create_test_assessment(
            db_session, user, title="Active"
        )
        deleted_assessment = await create_test_assessment(
            db_session, user, title="Deleted"
        )
        await db_session.commit()

        # Soft delete one assessment
        await test_client.delete(f"/assessments/{deleted_assessment.id}")

        # List assessments
        response = await test_client.get("/assessments")

        assert response.status_code == 200
        data = response.json()
        assessment_ids = [a["id"] for a in data]
        assert str(active_assessment.id) in assessment_ids
        assert str(deleted_assessment.id) not in assessment_ids


@pytest.mark.integration
@pytest.mark.assessments
class TestGetAssessment:
    """Tests for GET /assessments/{assessment_id} endpoint."""

    @pytest.mark.asyncio
    async def test_get_assessment_success(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test getting an assessment successfully."""
        assessment = await create_test_assessment(
            db_session, user, title="Test Assessment"
        )
        await db_session.commit()

        response = await test_client.get(f"/assessments/{assessment.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(assessment.id)
        assert data["title"] == "Test Assessment"
        assert "questions" in data
        assert data["questions"] == []

    @pytest.mark.asyncio
    async def test_get_assessment_with_questions_in_order(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test getting assessment includes questions in correct order."""
        assessment = await create_test_assessment(db_session, user)
        question1 = await create_test_question(db_session, user, question_text="Q1")
        question2 = await create_test_question(db_session, user, question_text="Q2")
        question3 = await create_test_question(db_session, user, question_text="Q3")
        await db_session.commit()

        await link_question_to_assessment(
            db_session, assessment.id, question1.id, order=0
        )
        await link_question_to_assessment(
            db_session, assessment.id, question2.id, order=1
        )
        await link_question_to_assessment(
            db_session, assessment.id, question3.id, order=2
        )
        await db_session.commit()

        response = await test_client.get(f"/assessments/{assessment.id}")

        assert response.status_code == 200
        data = response.json()
        assert len(data["questions"]) == 3
        # Verify order
        assert data["questions"][0]["question_text"] == "Q1"
        assert data["questions"][0]["order"] == 0
        assert data["questions"][1]["question_text"] == "Q2"
        assert data["questions"][1]["order"] == 1
        assert data["questions"][2]["question_text"] == "Q3"
        assert data["questions"][2]["order"] == 2

    @pytest.mark.asyncio
    async def test_get_assessment_not_found(
        self, test_client: AsyncClient, user: User
    ) -> None:
        """Test getting non-existent assessment returns 404."""
        import uuid

        non_existent_id = uuid.uuid4()
        response = await test_client.get(f"/assessments/{non_existent_id}")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_get_assessment_soft_deleted_returns_404(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test getting soft-deleted assessment returns 404."""
        assessment = await create_test_assessment(db_session, user)
        await db_session.commit()

        # Soft delete the assessment
        await test_client.delete(f"/assessments/{assessment.id}")

        # Try to get the soft-deleted assessment
        response = await test_client.get(f"/assessments/{assessment.id}")

        assert response.status_code == 404


@pytest.mark.integration
@pytest.mark.assessments
class TestUpdateAssessment:
    """Tests for PATCH /assessments/{assessment_id} endpoint."""

    @pytest.mark.asyncio
    async def test_update_assessment_title(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test updating assessment title successfully."""
        assessment = await create_test_assessment(db_session, user, title="Old Title")
        await db_session.commit()

        update_data = {"title": "New Title"}
        response = await test_client.patch(
            f"/assessments/{assessment.id}", json=update_data
        )

        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "New Title"

    @pytest.mark.asyncio
    async def test_update_assessment_description(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test updating assessment description successfully."""
        assessment = await create_test_assessment(
            db_session, user, description="Old description"
        )
        await db_session.commit()

        update_data = {"description": "New description"}
        response = await test_client.patch(
            f"/assessments/{assessment.id}", json=update_data
        )

        assert response.status_code == 200
        data = response.json()
        assert data["description"] == "New description"

    @pytest.mark.asyncio
    async def test_update_assessment_move_to_folder(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test moving assessment to different folder."""
        folder1 = await create_test_folder(db_session, user, name="Folder 1")
        folder2 = await create_test_folder(db_session, user, name="Folder 2")
        assessment = await create_test_assessment(db_session, user, folder=folder1)
        await db_session.commit()

        update_data = {"folder_id": str(folder2.id)}
        response = await test_client.patch(
            f"/assessments/{assessment.id}", json=update_data
        )

        assert response.status_code == 200
        data = response.json()
        assert data["folder_id"] == str(folder2.id)

    @pytest.mark.asyncio
    async def test_update_assessment_not_found(
        self, test_client: AsyncClient, user: User
    ) -> None:
        """Test updating non-existent assessment returns 404."""
        import uuid

        non_existent_id = uuid.uuid4()
        update_data = {"title": "New Title"}
        response = await test_client.patch(
            f"/assessments/{non_existent_id}", json=update_data
        )

        assert response.status_code == 404


@pytest.mark.integration
@pytest.mark.assessments
class TestSoftDeleteAssessment:
    """Tests for DELETE /assessments/{assessment_id} endpoint."""

    @pytest.mark.asyncio
    async def test_soft_delete_assessment_success(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test soft deleting assessment successfully."""
        assessment = await create_test_assessment(db_session, user)
        await db_session.commit()

        response = await test_client.delete(f"/assessments/{assessment.id}")

        assert response.status_code == 204

        # Verify assessment has deleted_at timestamp
        await db_session.refresh(assessment)
        assert assessment.deleted_at is not None

    @pytest.mark.asyncio
    async def test_soft_delete_assessment_not_in_list(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test soft-deleted assessment not in list results."""
        assessment = await create_test_assessment(db_session, user)
        await db_session.commit()

        # Soft delete assessment
        await test_client.delete(f"/assessments/{assessment.id}")

        # List assessments
        response = await test_client.get("/assessments")

        assert response.status_code == 200
        data = response.json()
        assessment_ids = [a["id"] for a in data]
        assert str(assessment.id) not in assessment_ids

    @pytest.mark.asyncio
    async def test_soft_delete_assessment_not_found(
        self, test_client: AsyncClient, user: User
    ) -> None:
        """Test soft deleting non-existent assessment returns 404."""
        import uuid

        non_existent_id = uuid.uuid4()
        response = await test_client.delete(f"/assessments/{non_existent_id}")

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_soft_delete_assessment_cleans_up_orphaned_questions(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test that deleting assessment triggers cleanup of orphaned questions."""
        from sqlalchemy import select

        from edcraft_backend.models.question import Question

        assessment = await create_test_assessment(db_session, user)

        orphaned_question = await create_test_question(
            db_session, user, question_text="Orphaned Question"
        )

        shared_question = await create_test_question(
            db_session, user, question_text="Shared Question"
        )
        other_assessment = await create_test_assessment(
            db_session, user, title="Other Assessment"
        )
        await db_session.commit()

        await test_client.post(
            f"/assessments/{assessment.id}/questions/link",
            json={"question_id": str(orphaned_question.id)},
        )

        await test_client.post(
            f"/assessments/{assessment.id}/questions/link",
            json={"question_id": str(shared_question.id)},
        )
        await test_client.post(
            f"/assessments/{other_assessment.id}/questions/link",
            json={"question_id": str(shared_question.id)},
        )

        response = await test_client.delete(f"/assessments/{assessment.id}")
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

    @pytest.mark.asyncio
    async def test_delete_assessment_preserves_question_still_in_use(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test that deleting assessment doesn't delete question still used in question bank."""
        from sqlalchemy import select

        from edcraft_backend.models.question import Question

        # Create assessment and question bank
        assessment = await create_test_assessment(db_session, user)
        question_bank = await create_test_question_bank(
            db_session, user, title="Test Question Bank"
        )

        # Create a question used in both assessment and question bank
        shared_question = await create_test_question(
            db_session, user, question_text="Question in both assessment and bank"
        )
        await db_session.commit()

        # Link question to both assessment and question bank
        await test_client.post(
            f"/assessments/{assessment.id}/questions/link",
            json={"question_id": str(shared_question.id)},
        )
        await link_question_to_question_bank(
            db_session, question_bank.id, shared_question.id
        )
        await db_session.commit()

        # Delete the assessment
        response = await test_client.delete(f"/assessments/{assessment.id}")
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
        ), "Question should remain active when still used in question bank"


@pytest.mark.integration
@pytest.mark.assessments
class TestLinkQuestionToAssessment:
    """Tests for POST /assessments/{assessment_id}/questions/link endpoint."""

    @pytest.mark.asyncio
    async def test_link_question_to_assessment_success(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test linking question to assessment successfully."""
        assessment = await create_test_assessment(db_session, user)
        question = await create_test_question(db_session, user)
        await db_session.commit()

        question_data: dict[str, Any] = {"question_id": str(question.id), "order": 0}
        response = await test_client.post(
            f"/assessments/{assessment.id}/questions/link", json=question_data
        )

        assert response.status_code == 201
        data = response.json()
        assert len(data["questions"]) == 1
        assert data["questions"][0]["id"] == str(question.id)
        assert data["questions"][0]["order"] == 0

    @pytest.mark.asyncio
    async def test_link_multiple_questions_with_order(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test linking multiple questions with specific order."""
        assessment = await create_test_assessment(db_session, user)
        question1 = await create_test_question(db_session, user)
        question2 = await create_test_question(db_session, user)
        question3 = await create_test_question(db_session, user)
        await db_session.commit()

        # Add questions with specific order
        await test_client.post(
            f"/assessments/{assessment.id}/questions/link",
            json={"question_id": str(question1.id), "order": 0},
        )
        await test_client.post(
            f"/assessments/{assessment.id}/questions/link",
            json={"question_id": str(question2.id), "order": 1},
        )
        response = await test_client.post(
            f"/assessments/{assessment.id}/questions/link",
            json={"question_id": str(question3.id), "order": 2},
        )

        assert response.status_code == 201
        data = response.json()
        assert len(data["questions"]) == 3
        assert data["questions"][0]["id"] == str(question1.id)
        assert data["questions"][1]["id"] == str(question2.id)
        assert data["questions"][2]["id"] == str(question3.id)

    @pytest.mark.asyncio
    async def test_link_question_default_order(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test linking question with default order (auto-increments)."""
        assessment = await create_test_assessment(db_session, user)
        question = await create_test_question(db_session, user)
        await db_session.commit()

        question_data = {"question_id": str(question.id)}
        response = await test_client.post(
            f"/assessments/{assessment.id}/questions/link", json=question_data
        )

        assert response.status_code == 201
        data = response.json()
        assert data["questions"][0]["order"] == 0

    @pytest.mark.asyncio
    async def test_link_question_to_nonexistent_assessment(
        self, test_client: AsyncClient, user: User
    ) -> None:
        """Test linking question to non-existent assessment returns 404."""
        import uuid

        non_existent_assessment_id = uuid.uuid4()
        question_data: dict[str, Any] = {"question_id": str(uuid.uuid4()), "order": 0}
        response = await test_client.post(
            f"/assessments/{non_existent_assessment_id}/questions/link",
            json=question_data,
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_link_nonexistent_question_to_assessment(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test linking non-existent question to assessment returns 404."""
        import uuid

        assessment = await create_test_assessment(db_session, user)
        await db_session.commit()

        non_existent_question_id = uuid.uuid4()
        question_data: dict[str, Any] = {
            "question_id": str(non_existent_question_id),
            "order": 0,
        }
        response = await test_client.post(
            f"/assessments/{assessment.id}/questions/link", json=question_data
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_link_question_with_insert_behavior(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test that linking question at existing order shifts other questions down."""
        assessment = await create_test_assessment(db_session, user)
        question1 = await create_test_question(db_session, user, question_text="Q1")
        question2 = await create_test_question(db_session, user, question_text="Q2")
        await db_session.commit()

        await test_client.post(
            f"/assessments/{assessment.id}/questions/link",
            json={"question_id": str(question1.id), "order": 0},
        )

        response = await test_client.post(
            f"/assessments/{assessment.id}/questions/link",
            json={"question_id": str(question2.id), "order": 0},
        )

        assert response.status_code == 201
        data = response.json()
        questions = data["questions"]

        assert len(questions) == 2
        assert questions[0]["question_text"] == "Q2"
        assert questions[0]["order"] == 0
        assert questions[1]["question_text"] == "Q1"
        assert questions[1]["order"] == 1

    @pytest.mark.asyncio
    async def test_link_question_insert_in_middle(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test linking question in middle shifts questions at/after position down."""
        assessment = await create_test_assessment(db_session, user)
        q1 = await create_test_question(db_session, user, question_text="Q1")
        q2 = await create_test_question(db_session, user, question_text="Q2")
        q3 = await create_test_question(db_session, user, question_text="Q3")
        q4 = await create_test_question(db_session, user, question_text="Q4")
        q_new = await create_test_question(db_session, user, question_text="Q_NEW")
        await db_session.commit()

        # Add initial questions
        for q in [q1, q2, q3, q4]:
            await test_client.post(
                f"/assessments/{assessment.id}/questions/link",
                json={"question_id": str(q.id)},
            )

        # Insert at position 2 (between Q2 and Q3)
        response = await test_client.post(
            f"/assessments/{assessment.id}/questions/link",
            json={"question_id": str(q_new.id), "order": 2},
        )

        assert response.status_code == 201
        data = response.json()
        questions = data["questions"]

        # Verify order: Q1, Q2, Q_NEW, Q3, Q4
        assert len(questions) == 5
        assert questions[0]["question_text"] == "Q1"
        assert questions[0]["order"] == 0
        assert questions[1]["question_text"] == "Q2"
        assert questions[1]["order"] == 1
        assert questions[2]["question_text"] == "Q_NEW"
        assert questions[2]["order"] == 2
        assert questions[3]["question_text"] == "Q3"
        assert questions[3]["order"] == 3
        assert questions[4]["question_text"] == "Q4"
        assert questions[4]["order"] == 4

    @pytest.mark.asyncio
    async def test_link_question_with_order_exceeding_count(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test linking with order > count fails with validation error."""
        assessment = await create_test_assessment(db_session, user)
        q1 = await create_test_question(db_session, user, question_text="Q1")
        q2 = await create_test_question(db_session, user, question_text="Q2")
        q_new = await create_test_question(db_session, user, question_text="Q_NEW")
        await db_session.commit()

        # Add two questions (count=2)
        await test_client.post(
            f"/assessments/{assessment.id}/questions/link",
            json={"question_id": str(q1.id)},
        )
        await test_client.post(
            f"/assessments/{assessment.id}/questions/link",
            json={"question_id": str(q2.id)},
        )

        response = await test_client.post(
            f"/assessments/{assessment.id}/questions/link",
            json={"question_id": str(q_new.id), "order": 10},
        )

        assert response.status_code == 400
        assert "Order must be between 0 and 2" in response.json()["detail"]
        assert "Omit order to append" in response.json()["detail"]


@pytest.mark.integration
@pytest.mark.assessments
class TestInsertQuestionIntoAssessment:
    """Tests for POST /assessments/{assessment_id}/questions endpoint."""

    @pytest.mark.asyncio
    async def test_insert_question_into_assessment_success(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test inserting a new question into assessment successfully."""
        assessment = await create_test_assessment(db_session, user)
        await db_session.commit()

        question_data: dict[str, Any] = {
            "question": {
                "question_type": "mcq",
                "question_text": "What is 2+2?",
                "data": {
                    "options": ["3", "4", "5", "6"],
                    "correct_index": 1,
                },
            },
            "order": 0,
        }
        response = await test_client.post(
            f"/assessments/{assessment.id}/questions", json=question_data
        )

        assert response.status_code == 201
        data = response.json()
        assert len(data["questions"]) == 1
        assert data["questions"][0]["question_text"] == "What is 2+2?"
        assert data["questions"][0]["question_type"] == "mcq"
        assert data["questions"][0]["order"] == 0

    @pytest.mark.asyncio
    async def test_insert_question_with_default_order(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test inserting question with default order (auto-increments)."""
        assessment = await create_test_assessment(db_session, user)
        await db_session.commit()

        question_data: dict[str, Any] = {
            "question": {
                "question_type": "short_answer",
                "question_text": "What is 2+2?",
                "data": {
                    "correct_answer": "4",
                },
            }
        }
        response = await test_client.post(
            f"/assessments/{assessment.id}/questions", json=question_data
        )

        assert response.status_code == 201
        data = response.json()
        assert len(data["questions"]) == 1
        assert data["questions"][0]["order"] == 0

    @pytest.mark.asyncio
    async def test_insert_multiple_questions_auto_order(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test inserting multiple questions with auto-incrementing order."""
        assessment = await create_test_assessment(db_session, user)
        await db_session.commit()

        # Insert first question
        question1_data: dict[str, Any] = {
            "question": {
                "question_type": "short_answer",
                "question_text": "The sky is blue. True or False?",
                "data": {"correct_answer": "True"},
            }
        }
        await test_client.post(
            f"/assessments/{assessment.id}/questions", json=question1_data
        )

        # Insert second question (should auto-increment to order 1)
        question2_data: dict[str, Any] = {
            "question": {
                "question_type": "short_answer",
                "question_text": "Water freezes at 100°C. True or False?",
                "data": {"correct_answer": "False"},
            }
        }
        response = await test_client.post(
            f"/assessments/{assessment.id}/questions", json=question2_data
        )

        assert response.status_code == 201
        data = response.json()
        assert len(data["questions"]) == 2
        assert data["questions"][0]["order"] == 0
        assert data["questions"][1]["order"] == 1

    @pytest.mark.asyncio
    async def test_insert_question_into_nonexistent_assessment(
        self, test_client: AsyncClient, user: User
    ) -> None:
        """Test inserting question into non-existent assessment returns 404."""
        import uuid

        non_existent_assessment_id = uuid.uuid4()
        question_data: dict[str, Any] = {
            "question": {
                "question_type": "short_answer",
                "question_text": "Test question",
                "data": {
                    "correct_answer": "answer",
                },
            },
            "order": 0,
        }
        response = await test_client.post(
            f"/assessments/{non_existent_assessment_id}/questions", json=question_data
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_insert_question_with_specific_order(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test inserting question with specific order position."""
        assessment = await create_test_assessment(db_session, user)
        await db_session.commit()

        # Insert question at order 0
        question_data: dict[str, Any] = {
            "question": {
                "question_type": "short_answer",
                "question_text": "What is 1+1?",
                "data": {
                    "correct_answer": "2",
                },
            },
            "order": 0,
        }
        response = await test_client.post(
            f"/assessments/{assessment.id}/questions", json=question_data
        )

        assert response.status_code == 201
        data = response.json()
        assert data["questions"][0]["order"] == 0

    @pytest.mark.asyncio
    async def test_insert_question_with_insert_behavior(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test that inserting question at existing order shifts other questions down."""
        assessment = await create_test_assessment(db_session, user)
        await db_session.commit()

        question1_data: dict[str, Any] = {
            "question": {
                "question_type": "short_answer",
                "question_text": "Question 1",
                "data": {
                    "correct_answer": "Answer 1",
                },
            },
            "order": 0,
        }
        await test_client.post(
            f"/assessments/{assessment.id}/questions", json=question1_data
        )

        question2_data: dict[str, Any] = {
            "question": {
                "question_type": "short_answer",
                "question_text": "Question 2",
                "data": {
                    "correct_answer": "Answer 2",
                },
            },
            "order": 0,
        }
        response = await test_client.post(
            f"/assessments/{assessment.id}/questions", json=question2_data
        )

        assert response.status_code == 201
        data = response.json()
        questions = data["questions"]

        assert len(questions) == 2
        assert questions[0]["question_text"] == "Question 2"
        assert questions[0]["order"] == 0
        assert questions[1]["question_text"] == "Question 1"
        assert questions[1]["order"] == 1


@pytest.mark.integration
@pytest.mark.assessments
class TestRemoveQuestionFromAssessment:
    """Tests for DELETE /assessments/{assessment_id}/questions/{question_id} endpoint."""

    @pytest.mark.asyncio
    async def test_remove_question_from_assessment_success(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test removing question from assessment successfully."""
        assessment = await create_test_assessment(db_session, user)
        question = await create_test_question(db_session, user)
        await db_session.commit()

        # Add question
        await link_question_to_assessment(db_session, assessment.id, question.id)
        await db_session.commit()

        # Remove question
        response = await test_client.delete(
            f"/assessments/{assessment.id}/questions/{question.id}"
        )

        assert response.status_code == 204

        # Verify question removed
        get_response = await test_client.get(f"/assessments/{assessment.id}")
        assert len(get_response.json()["questions"]) == 0

    @pytest.mark.asyncio
    async def test_remove_question_preserves_other_questions(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test removing one question preserves other questions."""
        assessment = await create_test_assessment(db_session, user)
        question1 = await create_test_question(db_session, user)
        question2 = await create_test_question(db_session, user)
        await db_session.commit()

        # Add both questions
        await link_question_to_assessment(
            db_session, assessment.id, question1.id, order=0
        )
        await link_question_to_assessment(
            db_session, assessment.id, question2.id, order=1
        )
        await db_session.commit()

        # Remove first question
        await test_client.delete(
            f"/assessments/{assessment.id}/questions/{question1.id}"
        )

        # Verify only second question remains
        response = await test_client.get(f"/assessments/{assessment.id}")
        data = response.json()
        assert len(data["questions"]) == 1
        assert data["questions"][0]["id"] == str(question2.id)

    @pytest.mark.asyncio
    async def test_remove_question_from_nonexistent_assessment(
        self, test_client: AsyncClient, user: User
    ) -> None:
        """Test removing question from non-existent assessment returns 404."""
        import uuid

        non_existent_assessment_id = uuid.uuid4()
        question_id = uuid.uuid4()
        response = await test_client.delete(
            f"/assessments/{non_existent_assessment_id}/questions/{question_id}"
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_remove_nonexistent_question_from_assessment(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test removing non-existent question from assessment returns 404."""
        import uuid

        assessment = await create_test_assessment(db_session, user)
        await db_session.commit()

        non_existent_question_id = uuid.uuid4()
        response = await test_client.delete(
            f"/assessments/{assessment.id}/questions/{non_existent_question_id}"
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_remove_question_normalizes_orders(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test that removing a question normalizes remaining orders."""
        assessment = await create_test_assessment(db_session, user)
        question1 = await create_test_question(db_session, user, question_text="Q1")
        question2 = await create_test_question(db_session, user, question_text="Q2")
        question3 = await create_test_question(db_session, user, question_text="Q3")
        await db_session.commit()

        await test_client.post(
            f"/assessments/{assessment.id}/questions/link",
            json={"question_id": str(question1.id), "order": 0},
        )
        await test_client.post(
            f"/assessments/{assessment.id}/questions/link",
            json={"question_id": str(question2.id), "order": 1},
        )
        await test_client.post(
            f"/assessments/{assessment.id}/questions/link",
            json={"question_id": str(question3.id), "order": 2},
        )

        await test_client.delete(
            f"/assessments/{assessment.id}/questions/{question2.id}"
        )

        response = await test_client.get(f"/assessments/{assessment.id}")
        data = response.json()

        assert len(data["questions"]) == 2
        assert data["questions"][0]["question_text"] == "Q1"
        assert data["questions"][0]["order"] == 0
        assert data["questions"][1]["question_text"] == "Q3"
        assert data["questions"][1]["order"] == 1

    @pytest.mark.asyncio
    async def test_remove_question_cleans_up_orphaned_question(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test that removing a question triggers cleanup if it becomes orphaned."""
        from sqlalchemy import select

        from edcraft_backend.models.question import Question

        assessment = await create_test_assessment(db_session, user)

        orphaned_question = await create_test_question(
            db_session, user, question_text="Will be orphaned"
        )

        shared_question = await create_test_question(
            db_session, user, question_text="Shared"
        )
        other_assessment = await create_test_assessment(
            db_session, user, title="Other Assessment"
        )
        await db_session.commit()

        await link_question_to_assessment(
            db_session, assessment.id, orphaned_question.id, order=0
        )
        await link_question_to_assessment(
            db_session, assessment.id, shared_question.id, order=1
        )
        await link_question_to_assessment(
            db_session, other_assessment.id, shared_question.id, order=0
        )
        await db_session.commit()

        response = await test_client.delete(
            f"/assessments/{assessment.id}/questions/{orphaned_question.id}"
        )
        assert response.status_code == 204

        assessment_id = assessment.id
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

        await test_client.delete(
            f"/assessments/{assessment_id}/questions/{shared_q_id}"
        )

        db_session.expire_all()
        shared_q_result = await db_session.execute(
            select(Question).where(Question.id == shared_q_id)
        )
        shared_q = shared_q_result.scalar_one_or_none()
        assert shared_q is not None
        assert (
            shared_q.deleted_at is None
        ), "Shared question should remain active while still in use"


@pytest.mark.integration
@pytest.mark.assessments
class TestReorderQuestions:
    """Tests for PATCH /assessments/{assessment_id}/questions/reorder endpoint."""

    @pytest.mark.asyncio
    async def test_reorder_questions_success(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test reordering questions successfully."""
        assessment = await create_test_assessment(db_session, user)
        question1 = await create_test_question(db_session, user, question_text="Q1")
        question2 = await create_test_question(db_session, user, question_text="Q2")
        question3 = await create_test_question(db_session, user, question_text="Q3")
        await db_session.commit()

        # Add questions in initial order
        await test_client.post(
            f"/assessments/{assessment.id}/questions/link",
            json={"question_id": str(question1.id), "order": 0},
        )
        await test_client.post(
            f"/assessments/{assessment.id}/questions/link",
            json={"question_id": str(question2.id), "order": 1},
        )
        await test_client.post(
            f"/assessments/{assessment.id}/questions/link",
            json={"question_id": str(question3.id), "order": 2},
        )

        # Reorder: reverse the order
        reorder_data: dict[str, Any] = {
            "question_orders": [
                {"question_id": str(question3.id), "order": 0},
                {"question_id": str(question2.id), "order": 1},
                {"question_id": str(question1.id), "order": 2},
            ]
        }
        response = await test_client.patch(
            f"/assessments/{assessment.id}/questions/reorder", json=reorder_data
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["questions"]) == 3
        assert data["questions"][0]["question_text"] == "Q3"
        assert data["questions"][1]["question_text"] == "Q2"
        assert data["questions"][2]["question_text"] == "Q1"

    @pytest.mark.asyncio
    async def test_reorder_questions_requires_all_questions(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test that partial reorder is rejected (requires all questions)."""
        assessment = await create_test_assessment(db_session, user)
        question1 = await create_test_question(db_session, user)
        question2 = await create_test_question(db_session, user)
        question3 = await create_test_question(db_session, user)
        await db_session.commit()

        # Add questions
        await test_client.post(
            f"/assessments/{assessment.id}/questions/link",
            json={"question_id": str(question1.id), "order": 0},
        )
        await test_client.post(
            f"/assessments/{assessment.id}/questions/link",
            json={"question_id": str(question2.id), "order": 1},
        )
        await test_client.post(
            f"/assessments/{assessment.id}/questions/link",
            json={"question_id": str(question3.id), "order": 2},
        )

        reorder_data: dict[str, Any] = {
            "question_orders": [
                {"question_id": str(question2.id), "order": 0},
                {"question_id": str(question1.id), "order": 1},
            ]
        }
        response = await test_client.patch(
            f"/assessments/{assessment.id}/questions/reorder", json=reorder_data
        )

        assert response.status_code == 400
        assert "must include all questions" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_reorder_questions_nonexistent_assessment(
        self, test_client: AsyncClient, user: User
    ) -> None:
        """Test reordering questions in non-existent assessment returns 404."""
        import uuid

        non_existent_id = uuid.uuid4()
        reorder_data: dict[str, Any] = {
            "question_orders": [{"question_id": str(uuid.uuid4()), "order": 0}]
        }
        response = await test_client.patch(
            f"/assessments/{non_existent_id}/questions/reorder", json=reorder_data
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_reorder_normalizes_to_consecutive_integers(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test that reorder normalizes orders to 0, 1, 2, 3..."""
        assessment = await create_test_assessment(db_session, user)
        question1 = await create_test_question(db_session, user, question_text="Q1")
        question2 = await create_test_question(db_session, user, question_text="Q2")
        question3 = await create_test_question(db_session, user, question_text="Q3")
        await db_session.commit()

        # Add questions
        await test_client.post(
            f"/assessments/{assessment.id}/questions/link",
            json={"question_id": str(question1.id)},
        )
        await test_client.post(
            f"/assessments/{assessment.id}/questions/link",
            json={"question_id": str(question2.id)},
        )
        await test_client.post(
            f"/assessments/{assessment.id}/questions/link",
            json={"question_id": str(question3.id)},
        )

        # Reorder with gaps (order: 5, 10, 100)
        reorder_data: dict[str, Any] = {
            "question_orders": [
                {"question_id": str(question1.id), "order": 100},
                {"question_id": str(question2.id), "order": 5},
                {"question_id": str(question3.id), "order": 10},
            ]
        }
        response = await test_client.patch(
            f"/assessments/{assessment.id}/questions/reorder", json=reorder_data
        )

        assert response.status_code == 200
        data = response.json()

        # Should be normalized to 0, 1, 2 based on the order they were sorted
        assert data["questions"][0]["question_text"] == "Q2"  # order 5 -> 0
        assert data["questions"][0]["order"] == 0
        assert data["questions"][1]["question_text"] == "Q3"  # order 10 -> 1
        assert data["questions"][1]["order"] == 1
        assert data["questions"][2]["question_text"] == "Q1"  # order 100 -> 2
        assert data["questions"][2]["order"] == 2
