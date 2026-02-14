"""Integration tests for Folders API endpoints."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from edcraft_backend.models.user import User
from tests.factories import (
    create_test_assessment,
    create_test_assessment_template,
    create_test_folder,
    create_test_folder_tree,
    create_test_question_bank,
    get_user_root_folder,
)


@pytest.mark.integration
@pytest.mark.folders
class TestCreateFolder:
    """Tests for POST /folders endpoint."""

    @pytest.mark.asyncio
    async def test_create_folder(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test creating folder with valid parent."""
        parent = await create_test_folder(db_session, user, name="Parent")
        await db_session.commit()

        folder_data = {
            "parent_id": str(parent.id),
            "name": "Child Folder",
            "description": "Nested folder",
        }
        response = await test_client.post("/folders", json=folder_data)

        assert response.status_code == 201
        data = response.json()
        assert data["parent_id"] == str(parent.id)
        assert data["name"] == "Child Folder"

    @pytest.mark.asyncio
    async def test_create_folder_duplicate_name_same_parent(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test duplicate folder name under same parent returns 409."""
        parent = await create_test_folder(db_session, user, name="Parent")
        await create_test_folder(db_session, user, parent=parent, name="Duplicate")
        await db_session.commit()

        folder_data = {
            "parent_id": str(parent.id),
            "name": "Duplicate",
        }
        response = await test_client.post("/folders", json=folder_data)

        assert response.status_code == 409

    @pytest.mark.asyncio
    async def test_create_folder_same_name_different_parent(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test same folder name under different parent is allowed."""
        parent1 = await create_test_folder(db_session, user, name="Parent1")
        parent2 = await create_test_folder(db_session, user, name="Parent2")
        await create_test_folder(db_session, user, parent=parent1, name="SameName")
        await db_session.commit()

        folder_data = {
            "parent_id": str(parent2.id),
            "name": "SameName",
        }
        response = await test_client.post("/folders", json=folder_data)

        assert response.status_code == 201

    @pytest.mark.asyncio
    async def test_create_folder_nonexistent_parent(
        self, test_client: AsyncClient, user: User
    ) -> None:
        """Test creating folder with non-existent parent returns 404."""
        import uuid

        folder_data = {
            "parent_id": str(uuid.uuid4()),
            "name": "Test Folder",
        }
        response = await test_client.post("/folders", json=folder_data)

        assert response.status_code == 404


@pytest.mark.integration
@pytest.mark.folders
class TestListFolders:
    """Tests for GET /folders endpoint."""

    @pytest.mark.asyncio
    async def test_list_folders_for_user(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test listing all folders for a user."""
        root_folder = await get_user_root_folder(db_session, user)
        folder1 = await create_test_folder(db_session, user, name="Folder1")
        folder2 = await create_test_folder(db_session, user, name="Folder2")
        nested_child = await create_test_folder(
            db_session, user, parent=folder1, name="NestedChild"
        )
        await db_session.commit()

        response = await test_client.get("/folders")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 4
        folder_ids = [f["id"] for f in data]
        assert str(root_folder.id) in folder_ids
        assert str(folder1.id) in folder_ids
        assert str(folder2.id) in folder_ids
        assert str(nested_child.id) in folder_ids

    @pytest.mark.asyncio
    async def test_list_folders_filter_by_parent(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test filtering folders by parent_id to get children."""
        parent = await create_test_folder(db_session, user, name="Parent")
        child1 = await create_test_folder(
            db_session, user, parent=parent, name="Child1"
        )
        child2 = await create_test_folder(
            db_session, user, parent=parent, name="Child2"
        )
        await create_test_folder(db_session, user, name="Other")
        await db_session.commit()

        response = await test_client.get(
            "/folders",
            params={"parent_id": str(parent.id)},
        )

        assert response.status_code == 200
        data = response.json()
        folder_ids = [f["id"] for f in data]
        assert str(child1.id) in folder_ids
        assert str(child2.id) in folder_ids
        assert all(f["parent_id"] == str(parent.id) for f in data)

    @pytest.mark.asyncio
    async def test_list_folders_excludes_soft_deleted(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test that soft-deleted folders are not in list."""
        active = await create_test_folder(db_session, user, name="Active")
        deleted = await create_test_folder(db_session, user, name="Deleted")
        await db_session.commit()

        await test_client.delete(f"/folders/{deleted.id}")

        response = await test_client.get("/folders")

        assert response.status_code == 200
        data = response.json()
        folder_ids = [f["id"] for f in data]
        assert str(active.id) in folder_ids
        assert str(deleted.id) not in folder_ids


@pytest.mark.integration
@pytest.mark.folders
class TestGetFolder:
    """Tests for GET /folders/{folder_id} endpoint."""

    @pytest.mark.asyncio
    async def test_get_folder_success(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test getting a folder successfully."""
        folder = await create_test_folder(
            db_session, user, name="Test Folder", description="Test desc"
        )
        await db_session.commit()

        response = await test_client.get(f"/folders/{folder.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(folder.id)
        assert data["name"] == "Test Folder"
        assert data["description"] == "Test desc"

    @pytest.mark.asyncio
    async def test_get_folder_not_found(
        self, test_client: AsyncClient, user: User
    ) -> None:
        """Test getting non-existent folder returns 404."""
        import uuid

        response = await test_client.get(f"/folders/{uuid.uuid4()}")

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_folder_soft_deleted_returns_404(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test getting soft-deleted folder returns 404."""
        folder = await create_test_folder(db_session, user)
        await db_session.commit()

        await test_client.delete(f"/folders/{folder.id}")
        response = await test_client.get(f"/folders/{folder.id}")

        assert response.status_code == 404


@pytest.mark.integration
@pytest.mark.folders
class TestGetFolderTree:
    """Tests for GET /folders/{folder_id}/tree endpoint."""

    @pytest.mark.asyncio
    async def test_get_folder_tree_with_children(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test getting folder tree with nested children."""
        folders = await create_test_folder_tree(db_session, user, depth=3)
        await db_session.commit()

        root = folders[0]
        response = await test_client.get(f"/folders/{root.id}/tree")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(root.id)
        assert "children" in data
        assert len(data["children"]) == 2

    @pytest.mark.asyncio
    async def test_get_folder_tree_includes_all_descendants(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test tree includes all descendant folders."""
        folders = await create_test_folder_tree(db_session, user, depth=3)
        await db_session.commit()

        root = folders[0]
        response = await test_client.get(f"/folders/{root.id}/tree")

        assert response.status_code == 200
        data = response.json()
        # Root has 2 children, each child has 2 grandchildren
        assert len(data["children"]) == 2
        assert len(data["children"][0]["children"]) == 2
        assert len(data["children"][1]["children"]) == 2

    @pytest.mark.asyncio
    async def test_get_folder_tree_excludes_soft_deleted_children(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test soft-deleted children not included in tree."""
        parent = await create_test_folder(db_session, user, name="Parent")
        child1 = await create_test_folder(
            db_session, user, parent=parent, name="Child1"
        )
        child2 = await create_test_folder(
            db_session, user, parent=parent, name="Child2"
        )
        await db_session.commit()

        await test_client.delete(f"/folders/{child2.id}")

        response = await test_client.get(f"/folders/{parent.id}/tree")

        assert response.status_code == 200
        data = response.json()
        child_ids = [c["id"] for c in data["children"]]
        assert str(child1.id) in child_ids
        assert str(child2.id) not in child_ids


@pytest.mark.integration
@pytest.mark.folders
class TestGetFolderPath:
    """Tests for GET /folders/{folder_id}/path endpoint."""

    @pytest.mark.asyncio
    async def test_get_folder_path_from_root(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test getting path from root to folder."""
        folders = await create_test_folder_tree(db_session, user, depth=3)
        await db_session.commit()

        # Get path to a grandchild (last in list)
        grandchild = folders[-1]
        response = await test_client.get(f"/folders/{grandchild.id}/path")

        assert response.status_code == 200
        data = response.json()
        assert "path" in data
        assert len(data["path"]) == 4

    @pytest.mark.asyncio
    async def test_get_folder_path_correct_order(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test path is in correct order (root to leaf)."""
        root_folder = await get_user_root_folder(db_session, user)

        child = await create_test_folder(
            db_session, user, parent=root_folder, name="Child"
        )
        grandchild = await create_test_folder(
            db_session, user, parent=child, name="Grandchild"
        )
        await db_session.commit()

        response = await test_client.get(f"/folders/{grandchild.id}/path")

        assert response.status_code == 200
        data = response.json()
        path = data["path"]
        assert len(path) == 3
        assert path[0]["name"] == "My Projects"
        assert path[1]["name"] == "Child"
        assert path[2]["name"] == "Grandchild"

    @pytest.mark.asyncio
    async def test_get_folder_path_root_only(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test root folder returns path with only itself."""
        root_folder = await get_user_root_folder(db_session, user)
        await db_session.commit()

        response = await test_client.get(f"/folders/{root_folder.id}/path")

        assert response.status_code == 200
        data = response.json()
        assert len(data["path"]) == 1
        assert data["path"][0]["id"] == str(root_folder.id)
        assert data["path"][0]["name"] == "My Projects"


@pytest.mark.integration
@pytest.mark.folders
class TestUpdateFolder:
    """Tests for PATCH /folders/{folder_id} endpoint."""

    @pytest.mark.asyncio
    async def test_update_folder_name(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test updating folder name successfully."""
        folder = await create_test_folder(db_session, user, name="Old Name")
        await db_session.commit()

        update_data = {"name": "New Name"}
        response = await test_client.patch(f"/folders/{folder.id}", json=update_data)

        assert response.status_code == 200
        assert response.json()["name"] == "New Name"

    @pytest.mark.asyncio
    async def test_update_folder_description(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test updating folder description successfully."""
        folder = await create_test_folder(db_session, user, description="Old desc")
        await db_session.commit()

        update_data = {"description": "New description"}
        response = await test_client.patch(f"/folders/{folder.id}", json=update_data)

        assert response.status_code == 200
        assert response.json()["description"] == "New description"

    @pytest.mark.asyncio
    async def test_update_folder_duplicate_name_same_parent(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test duplicate name under same parent returns 409."""
        parent = await create_test_folder(db_session, user, name="Parent")
        await create_test_folder(db_session, user, parent=parent, name="Existing")
        folder = await create_test_folder(
            db_session, user, parent=parent, name="ToRename"
        )
        await db_session.commit()

        update_data = {"name": "Existing"}
        response = await test_client.patch(f"/folders/{folder.id}", json=update_data)

        assert response.status_code == 409


@pytest.mark.integration
@pytest.mark.folders
class TestMoveFolder:
    """Tests for PATCH /folders/{folder_id}/move endpoint."""

    @pytest.mark.asyncio
    async def test_move_folder_to_new_parent(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test moving folder to new parent successfully."""
        old_parent = await create_test_folder(db_session, user, name="OldParent")
        new_parent = await create_test_folder(db_session, user, name="NewParent")
        folder = await create_test_folder(
            db_session, user, parent=old_parent, name="Folder"
        )
        await db_session.commit()

        move_data = {"parent_id": str(new_parent.id)}
        response = await test_client.patch(f"/folders/{folder.id}/move", json=move_data)

        assert response.status_code == 200
        assert response.json()["parent_id"] == str(new_parent.id)

    @pytest.mark.asyncio
    async def test_move_folder_circular_reference(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test circular reference (move to own child) returns 400."""
        parent = await create_test_folder(db_session, user, name="Parent")
        child = await create_test_folder(db_session, user, parent=parent, name="Child")
        await db_session.commit()

        move_data = {"parent_id": str(child.id)}
        response = await test_client.patch(f"/folders/{parent.id}/move", json=move_data)

        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_move_folder_nonexistent_parent(
        self, test_client: AsyncClient, user: User
    ) -> None:
        """Test moving to non-existent parent returns 404."""
        import uuid

        move_data = {"parent_id": str(uuid.uuid4())}
        response = await test_client.patch(
            f"/folders/{uuid.uuid4()}/move", json=move_data
        )

        assert response.status_code == 404


@pytest.mark.integration
@pytest.mark.folders
class TestSoftDeleteFolder:
    """Tests for DELETE /folders/{folder_id} endpoint."""

    @pytest.mark.asyncio
    async def test_soft_delete_folder_success(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test soft deleting folder successfully."""
        folder = await create_test_folder(db_session, user)
        await db_session.commit()

        response = await test_client.delete(f"/folders/{folder.id}")

        assert response.status_code == 204
        await db_session.refresh(folder)
        assert folder.deleted_at is not None

    @pytest.mark.asyncio
    async def test_soft_delete_folder_cascades_to_children(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test child folders cascade soft-deleted."""
        parent = await create_test_folder(db_session, user, name="Parent")
        child1 = await create_test_folder(
            db_session, user, parent=parent, name="Child1"
        )
        child2 = await create_test_folder(
            db_session, user, parent=parent, name="Child2"
        )
        await db_session.commit()

        response = await test_client.delete(f"/folders/{parent.id}")

        assert response.status_code == 204
        await db_session.refresh(parent)
        await db_session.refresh(child1)
        await db_session.refresh(child2)
        assert parent.deleted_at is not None
        assert child1.deleted_at is not None
        assert child2.deleted_at is not None

    @pytest.mark.asyncio
    async def test_soft_delete_folder_cascades_to_assessments(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test folder deletion cascades to assessments."""
        folder = await create_test_folder(db_session, user, name="Folder")
        assessment1 = await create_test_assessment(db_session, user, folder=folder)
        assessment2 = await create_test_assessment(db_session, user, folder=folder)
        await db_session.commit()

        response = await test_client.delete(f"/folders/{folder.id}")

        assert response.status_code == 204
        await db_session.refresh(folder)
        await db_session.refresh(assessment1)
        await db_session.refresh(assessment2)
        assert folder.deleted_at is not None
        assert assessment1.deleted_at is not None
        assert assessment2.deleted_at is not None

    @pytest.mark.asyncio
    async def test_soft_delete_folder_cascades_to_templates(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test folder deletion cascades to assessment templates."""
        folder = await create_test_folder(db_session, user, name="Folder")
        template1 = await create_test_assessment_template(
            db_session, user, folder=folder
        )
        template2 = await create_test_assessment_template(
            db_session, user, folder=folder
        )
        await db_session.commit()

        response = await test_client.delete(f"/folders/{folder.id}")

        assert response.status_code == 204
        await db_session.refresh(folder)
        await db_session.refresh(template1)
        await db_session.refresh(template2)
        assert folder.deleted_at is not None
        assert template1.deleted_at is not None
        assert template2.deleted_at is not None

    @pytest.mark.asyncio
    async def test_soft_delete_deeply_nested_folders(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test deletion works for deeply nested hierarchies."""
        # Create tree: root -> child -> grandchild -> great_grandchild
        root = await create_test_folder(db_session, user, name="Root")
        child = await create_test_folder(db_session, user, parent=root, name="Child")
        grandchild = await create_test_folder(
            db_session, user, parent=child, name="Grandchild"
        )
        great_grandchild = await create_test_folder(
            db_session, user, parent=grandchild, name="GreatGrandchild"
        )
        await db_session.commit()

        response = await test_client.delete(f"/folders/{root.id}")

        assert response.status_code == 204

        # Verify all levels are soft-deleted
        for folder in [root, child, grandchild, great_grandchild]:
            await db_session.refresh(folder)
            assert folder.deleted_at is not None

    @pytest.mark.asyncio
    async def test_soft_delete_folder_not_found(
        self, test_client: AsyncClient, user: User
    ) -> None:
        """Test soft deleting non-existent folder returns 404."""
        import uuid

        response = await test_client.delete(f"/folders/{uuid.uuid4()}")

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_cannot_delete_root_folder(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test that deleting root folder returns 403 Forbidden."""
        root_folder = await get_user_root_folder(db_session, user)
        await db_session.commit()

        response = await test_client.delete(f"/folders/{root_folder.id}")
        assert response.status_code == 403


@pytest.mark.integration
@pytest.mark.folders
class TestGetFolderContents:
    """Tests for GET /folders/{folder_id}/contents endpoint."""

    @pytest.mark.asyncio
    async def test_get_folder_contents_success(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test getting folder with contents successfully."""
        folder = await create_test_folder(
            db_session, user, name="Test Folder", description="Test desc"
        )
        child1 = await create_test_folder(
            db_session, user, parent=folder, name="Child 1"
        )
        child2 = await create_test_folder(
            db_session, user, parent=folder, name="Child 2"
        )
        assessment1 = await create_test_assessment(
            db_session, user, folder=folder, title="Assessment 1"
        )
        assessment2 = await create_test_assessment(
            db_session, user, folder=folder, title="Assessment 2"
        )
        template1 = await create_test_assessment_template(
            db_session, user, folder=folder, title="Template 1"
        )
        template2 = await create_test_assessment_template(
            db_session, user, folder=folder, title="Template 2"
        )
        question_bank1 = await create_test_question_bank(
            db_session, user, folder=folder, title="Question Bank 1"
        )
        question_bank2 = await create_test_question_bank(
            db_session, user, folder=folder, title="Question Bank 2"
        )
        await db_session.commit()

        response = await test_client.get(f"/folders/{folder.id}/contents")

        assert response.status_code == 200
        data = response.json()

        # Verify folder fields
        assert data["id"] == str(folder.id)
        assert data["name"] == "Test Folder"
        assert data["description"] == "Test desc"
        assert data["owner_id"] == str(user.id)

        # Verify assessments are included
        assert "assessments" in data
        assert len(data["assessments"]) == 2
        assessment_ids = [a["id"] for a in data["assessments"]]
        assert str(assessment1.id) in assessment_ids
        assert str(assessment2.id) in assessment_ids

        # Verify assessment templates are included
        assert "assessment_templates" in data
        assert len(data["assessment_templates"]) == 2
        template_ids = [t["id"] for t in data["assessment_templates"]]
        assert str(template1.id) in template_ids
        assert str(template2.id) in template_ids

        # Verify question banks are included
        assert "question_banks" in data
        assert len(data["question_banks"]) == 2
        question_bank_ids = [qb["id"] for qb in data["question_banks"]]
        assert str(question_bank1.id) in question_bank_ids
        assert str(question_bank2.id) in question_bank_ids

        # Verify child folders are included
        assert "folders" in data
        assert len(data["folders"]) == 2
        folder_ids = [f["id"] for f in data["folders"]]
        assert str(child1.id) in folder_ids
        assert str(child2.id) in folder_ids

    @pytest.mark.asyncio
    async def test_get_folder_contents_empty_folder(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test getting folder with no contents returns empty lists."""
        folder = await create_test_folder(db_session, user, name="Empty Folder")
        await db_session.commit()

        response = await test_client.get(f"/folders/{folder.id}/contents")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(folder.id)
        assert data["folders"] == []
        assert data["assessments"] == []
        assert data["assessment_templates"] == []

    @pytest.mark.asyncio
    async def test_get_folder_contents_not_found(
        self, test_client: AsyncClient, user: User
    ) -> None:
        """Test getting non-existent folder returns 404."""
        import uuid

        response = await test_client.get(f"/folders/{uuid.uuid4()}/contents")

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_folder_contents_soft_deleted_folder_returns_404(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test getting soft-deleted folder returns 404."""
        folder = await create_test_folder(db_session, user)
        await create_test_assessment(db_session, user, folder=folder)
        await db_session.commit()

        await test_client.delete(f"/folders/{folder.id}")
        response = await test_client.get(f"/folders/{folder.id}/contents")

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_folder_contents_excludes_soft_deleted_assessments(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test soft-deleted assessments are not included in contents."""
        folder = await create_test_folder(db_session, user)
        active_assessment = await create_test_assessment(
            db_session, user, folder=folder, title="Active"
        )
        deleted_assessment = await create_test_assessment(
            db_session, user, folder=folder, title="Deleted"
        )
        await db_session.commit()

        # Soft delete one assessment
        await test_client.delete(f"/assessments/{deleted_assessment.id}")

        response = await test_client.get(f"/folders/{folder.id}/contents")

        assert response.status_code == 200
        data = response.json()
        assessment_ids = [a["id"] for a in data["assessments"]]
        assert str(active_assessment.id) in assessment_ids
        assert str(deleted_assessment.id) not in assessment_ids

    @pytest.mark.asyncio
    async def test_get_folder_contents_excludes_soft_deleted_templates(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test soft-deleted templates are not included in contents."""
        folder = await create_test_folder(db_session, user)
        active_template = await create_test_assessment_template(
            db_session, user, folder=folder, title="Active"
        )
        deleted_template = await create_test_assessment_template(
            db_session, user, folder=folder, title="Deleted"
        )
        await db_session.commit()

        # Soft delete one template
        await test_client.delete(f"/assessment-templates/{deleted_template.id}")

        response = await test_client.get(f"/folders/{folder.id}/contents")

        assert response.status_code == 200
        data = response.json()
        template_ids = [t["id"] for t in data["assessment_templates"]]
        assert str(active_template.id) in template_ids
        assert str(deleted_template.id) not in template_ids

    @pytest.mark.asyncio
    async def test_get_folder_contents_excludes_soft_deleted_question_banks(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test soft-deleted question banks are not included in contents."""
        folder = await create_test_folder(db_session, user)
        active_qb = await create_test_question_bank(
            db_session, user, folder=folder, title="Active QB"
        )
        deleted_qb = await create_test_question_bank(
            db_session, user, folder=folder, title="Deleted QB"
        )
        await db_session.commit()

        # Soft delete one question bank
        await test_client.delete(f"/question-banks/{deleted_qb.id}")

        response = await test_client.get(f"/folders/{folder.id}/contents")

        assert response.status_code == 200
        data = response.json()
        qb_ids = [qb["id"] for qb in data["question_banks"]]
        assert str(active_qb.id) in qb_ids
        assert str(deleted_qb.id) not in qb_ids

    @pytest.mark.asyncio
    async def test_get_folder_contents_excludes_soft_deleted_child_folders(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test soft-deleted child folders are not included in contents."""
        folder = await create_test_folder(db_session, user, name="Parent")
        active_child = await create_test_folder(
            db_session, user, parent=folder, name="Active Child"
        )
        deleted_child = await create_test_folder(
            db_session, user, parent=folder, name="Deleted Child"
        )
        await db_session.commit()

        # Soft delete one child folder
        await test_client.delete(f"/folders/{deleted_child.id}")

        response = await test_client.get(f"/folders/{folder.id}/contents")

        assert response.status_code == 200
        data = response.json()

        folder_ids = [f["id"] for f in data["folders"]]
        assert str(active_child.id) in folder_ids
        assert str(deleted_child.id) not in folder_ids

    @pytest.mark.asyncio
    async def test_get_folder_contents_returns_complete_assessment_objects(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test assessments and templates have complete fields."""
        folder = await create_test_folder(db_session, user)
        assessment = await create_test_assessment(
            db_session,
            user,
            folder=folder,
            title="Test Assessment",
            description="Test description",
        )
        await db_session.commit()

        response = await test_client.get(f"/folders/{folder.id}/contents")

        assert response.status_code == 200
        data = response.json()

        # Verify assessment has all required fields
        assessment_data = data["assessments"][0]
        assert assessment_data["id"] == str(assessment.id)
        assert assessment_data["title"] == "Test Assessment"
        assert assessment_data["description"] == "Test description"
        assert assessment_data["owner_id"] == str(user.id)
        assert assessment_data["folder_id"] == str(folder.id)
        assert "created_at" in assessment_data
        assert "updated_at" in assessment_data

    @pytest.mark.asyncio
    async def test_get_folder_contents_returns_complete_question_bank_objects(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test question banks have complete fields."""
        folder = await create_test_folder(db_session, user)
        question_bank = await create_test_question_bank(
            db_session,
            user,
            folder=folder,
            title="Test Question Bank",
            description="QB description",
        )
        await db_session.commit()

        response = await test_client.get(f"/folders/{folder.id}/contents")

        assert response.status_code == 200
        data = response.json()

        # Verify question bank has all required fields
        qb_data = data["question_banks"][0]
        assert qb_data["id"] == str(question_bank.id)
        assert qb_data["title"] == "Test Question Bank"
        assert qb_data["description"] == "QB description"
        assert qb_data["owner_id"] == str(user.id)
        assert qb_data["folder_id"] == str(folder.id)
        assert "created_at" in qb_data
        assert "updated_at" in qb_data

    @pytest.mark.asyncio
    async def test_get_folder_contents_returns_complete_assessment_template_objects(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test assessments and templates have complete fields."""
        folder = await create_test_folder(db_session, user)
        template = await create_test_assessment_template(
            db_session,
            user,
            folder=folder,
            title="Test Template",
            description="Template desc",
        )
        await db_session.commit()

        response = await test_client.get(f"/folders/{folder.id}/contents")

        assert response.status_code == 200
        data = response.json()

        # Verify template has all required fields
        template_data = data["assessment_templates"][0]
        assert template_data["id"] == str(template.id)
        assert template_data["title"] == "Test Template"
        assert template_data["description"] == "Template desc"
        assert template_data["owner_id"] == str(user.id)
        assert template_data["folder_id"] == str(folder.id)
        assert "created_at" in template_data
        assert "updated_at" in template_data

    @pytest.mark.asyncio
    async def test_get_folder_contents_child_folders_have_correct_fields(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test child folders have all FolderResponse fields."""
        folder = await create_test_folder(db_session, user, name="Parent")
        child = await create_test_folder(
            db_session,
            user,
            parent=folder,
            name="Child",
            description="Child description",
        )
        await db_session.commit()

        response = await test_client.get(f"/folders/{folder.id}/contents")

        assert response.status_code == 200
        data = response.json()

        child_data = data["folders"][0]
        assert child_data["id"] == str(child.id)
        assert child_data["owner_id"] == str(user.id)
        assert child_data["parent_id"] == str(folder.id)
        assert child_data["name"] == "Child"
        assert child_data["description"] == "Child description"
        assert "created_at" in child_data
        assert "updated_at" in child_data

    @pytest.mark.asyncio
    async def test_get_folder_contents_child_folders_dont_include_nested_contents(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test child folders don't include their own contents (non-recursive)."""
        parent = await create_test_folder(db_session, user, name="Parent")
        child = await create_test_folder(db_session, user, parent=parent, name="Child")

        # Add content to child folder
        await create_test_assessment(db_session, user, folder=child)
        await create_test_folder(db_session, user, parent=child, name="Grandchild")
        await db_session.commit()

        response = await test_client.get(f"/folders/{parent.id}/contents")

        assert response.status_code == 200
        data = response.json()

        # Parent should have child folder
        assert len(data["folders"]) == 1
        child_data = data["folders"][0]

        # Child folder should only have FolderResponse fields (no nested contents)
        assert "assessments" not in child_data
        assert "assessment_templates" not in child_data
        assert "folders" not in child_data
