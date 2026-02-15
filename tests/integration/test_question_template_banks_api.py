"""Integration tests for Question Template Bank API endpoints."""

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from edcraft_backend.models.question_template import QuestionTemplate
from edcraft_backend.models.question_template_bank_question_template import (
    QuestionTemplateBankQuestionTemplate,
)
from edcraft_backend.models.user import User
from tests.factories import (
    create_question_template_bank_with_templates,
    create_test_folder,
    create_test_question_template,
    create_test_question_template_bank,
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

    @pytest.mark.asyncio
    async def test_soft_delete_cleans_up_orphaned_templates(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test that deleting a bank soft-deletes orphaned templates."""
        bank = await create_test_question_template_bank(db_session, user)
        other_bank = await create_test_question_template_bank(db_session, user)

        orphaned_template = await create_test_question_template(
            db_session, user, question_text="Orphaned template"
        )
        shared_template = await create_test_question_template(
            db_session, user, question_text="Shared template"
        )

        await link_question_template_to_question_template_bank(
            db_session, bank.id, orphaned_template.id
        )
        await link_question_template_to_question_template_bank(
            db_session, bank.id, shared_template.id
        )
        await link_question_template_to_question_template_bank(
            db_session, other_bank.id, shared_template.id
        )
        await db_session.commit()

        # Delete the bank
        response = await test_client.delete(f"/question-template-banks/{bank.id}")
        assert response.status_code == 204

        orphaned_template_id = orphaned_template.id
        shared_template_id = shared_template.id

        db_session.expire_all()
        orphaned_template_result = await db_session.execute(
            select(QuestionTemplate).where(QuestionTemplate.id == orphaned_template_id)
        )
        orphaned_template = orphaned_template_result.scalar_one()
        assert orphaned_template.deleted_at is not None

        shared_template_result = await db_session.execute(
            select(QuestionTemplate).where(QuestionTemplate.id == shared_template_id)
        )
        shared_template = shared_template_result.scalar_one()
        assert shared_template.deleted_at is None


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
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert len(data["question_templates"]) == 1
        assert data["question_templates"][0]["question_text"] == "What is 2+2?"

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
        """Test linking an existing question template to a bank."""
        bank = await create_test_question_template_bank(db_session, user)
        template = await create_test_question_template(
            db_session, user, question_text="Existing template"
        )
        await db_session.commit()

        response = await test_client.post(
            f"/question-template-banks/{bank.id}/question-templates/link",
            json={"question_template_id": str(template.id)},
        )

        assert response.status_code == 201
        data = response.json()
        assert len(data["question_templates"]) == 1
        assert data["question_templates"][0]["id"] == str(template.id)

    @pytest.mark.asyncio
    async def test_link_question_template_duplicate_fails(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test that linking the same template twice fails."""
        bank, templates = await create_question_template_bank_with_templates(
            db_session, user, num_templates=1
        )
        template = templates[0]
        await db_session.commit()

        # Try to link the same template again
        response = await test_client.post(
            f"/question-template-banks/{bank.id}/question-templates/link",
            json={"question_template_id": str(template.id)},
        )

        assert response.status_code == 409
        assert "already" in response.json()["detail"].lower()

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
        result = await db_session.execute(
            select(QuestionTemplateBankQuestionTemplate).where(
                QuestionTemplateBankQuestionTemplate.question_template_bank_id
                == bank.id,
                QuestionTemplateBankQuestionTemplate.question_template_id
                == template_to_remove.id,
            )
        )
        assert result.scalar_one_or_none() is None

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
class TestOrphanCleanup:
    """Tests for orphan cleanup logic across banks and assessment templates."""

    @pytest.mark.asyncio
    async def test_template_orphaned_when_removed_from_all_sources(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test template is orphaned when removed from all banks and assessments."""
        bank = await create_test_question_template_bank(db_session, user)
        template = await create_test_question_template(db_session, user)
        await link_question_template_to_question_template_bank(
            db_session, bank.id, template.id
        )
        await db_session.commit()

        # Remove from bank (only source)
        await test_client.delete(
            f"/question-template-banks/{bank.id}/question-templates/{template.id}"
        )

        # Template should be orphaned
        result = await db_session.execute(
            select(QuestionTemplate).where(QuestionTemplate.id == template.id)
        )
        orphaned_template = result.scalar_one()
        await db_session.refresh(orphaned_template)
        assert orphaned_template.deleted_at is not None

    @pytest.mark.asyncio
    async def test_template_not_orphaned_if_in_assessment_template(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test template is NOT orphaned if still in an assessment template."""
        from tests.factories import (
            create_test_assessment_template,
            link_question_template_to_assessment_template,
        )

        bank = await create_test_question_template_bank(db_session, user)
        assessment_template = await create_test_assessment_template(db_session, user)
        template = await create_test_question_template(db_session, user)

        # Link to both bank and assessment template
        await link_question_template_to_question_template_bank(
            db_session, bank.id, template.id
        )
        await link_question_template_to_assessment_template(
            db_session, assessment_template.id, template.id, order=0
        )
        await db_session.commit()

        # Remove from bank
        await test_client.delete(
            f"/question-template-banks/{bank.id}/question-templates/{template.id}"
        )

        # Template should NOT be orphaned (still in assessment template)
        result = await db_session.execute(
            select(QuestionTemplate).where(QuestionTemplate.id == template.id)
        )
        template_check = result.scalar_one()
        await db_session.refresh(template_check)
        assert template_check.deleted_at is None

    @pytest.mark.asyncio
    async def test_template_not_orphaned_if_in_another_bank(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test template is NOT orphaned if still in another bank."""
        bank1 = await create_test_question_template_bank(
            db_session, user, title="Bank 1"
        )
        bank2 = await create_test_question_template_bank(
            db_session, user, title="Bank 2"
        )
        template = await create_test_question_template(db_session, user)

        # Link to both banks
        await link_question_template_to_question_template_bank(
            db_session, bank1.id, template.id
        )
        await link_question_template_to_question_template_bank(
            db_session, bank2.id, template.id
        )
        await db_session.commit()

        # Remove from bank1
        await test_client.delete(
            f"/question-template-banks/{bank1.id}/question-templates/{template.id}"
        )

        # Template should NOT be orphaned (still in bank2)
        result = await db_session.execute(
            select(QuestionTemplate).where(QuestionTemplate.id == template.id)
        )
        template_check = result.scalar_one()
        await db_session.refresh(template_check)
        assert template_check.deleted_at is None
