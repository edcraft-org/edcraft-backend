"""Integration tests for Folders API endpoints."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.factories import (
    create_test_assessment,
    create_test_assessment_template,
    create_test_folder,
    create_test_folder_tree,
    create_test_user,
    get_user_root_folder,
)


@pytest.mark.integration
@pytest.mark.folders
class TestCreateFolder:
    """Tests for POST /folders endpoint."""

    @pytest.mark.asyncio
    async def test_create_root_folder(
        self, test_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test creating root folder (parent_id=None)."""
        user = await create_test_user(db_session)
        await db_session.commit()

        folder_data: dict[str, str | None] = {
            "owner_id": str(user.id),
            "parent_id": None,
            "name": "Root Folder",
            "description": "Top level folder",
        }
        response = await test_client.post("/folders", json=folder_data)

        assert response.status_code == 201
        data = response.json()
        assert data["owner_id"] == str(user.id)
        assert data["parent_id"] is None
        assert data["name"] == "Root Folder"
        assert "id" in data

    @pytest.mark.asyncio
    async def test_create_child_folder(
        self, test_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test creating child folder with valid parent."""
        user = await create_test_user(db_session)
        parent = await create_test_folder(db_session, user, name="Parent")
        await db_session.commit()

        folder_data = {
            "owner_id": str(user.id),
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
        self, test_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test duplicate folder name under same parent returns 409."""
        user = await create_test_user(db_session)
        parent = await create_test_folder(db_session, user, name="Parent")
        await create_test_folder(
            db_session, user, parent=parent, name="Duplicate"
        )
        await db_session.commit()

        folder_data = {
            "owner_id": str(user.id),
            "parent_id": str(parent.id),
            "name": "Duplicate",
        }
        response = await test_client.post("/folders", json=folder_data)

        assert response.status_code == 409

    @pytest.mark.asyncio
    async def test_create_folder_same_name_different_parent(
        self, test_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test same folder name under different parent is allowed."""
        user = await create_test_user(db_session)
        parent1 = await create_test_folder(db_session, user, name="Parent1")
        parent2 = await create_test_folder(db_session, user, name="Parent2")
        await create_test_folder(
            db_session, user, parent=parent1, name="SameName"
        )
        await db_session.commit()

        folder_data = {
            "owner_id": str(user.id),
            "parent_id": str(parent2.id),
            "name": "SameName",
        }
        response = await test_client.post("/folders", json=folder_data)

        assert response.status_code == 201

    @pytest.mark.asyncio
    async def test_create_folder_nonexistent_parent(
        self, test_client: AsyncClient
    ) -> None:
        """Test creating folder with non-existent parent returns 404."""
        import uuid

        folder_data = {
            "owner_id": str(uuid.uuid4()),
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
        self, test_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test listing all folders for a user."""
        user = await create_test_user(db_session)
        root_folder = await get_user_root_folder(db_session, user)
        folder1 = await create_test_folder(db_session, user, name="Folder1")
        folder2 = await create_test_folder(db_session, user, name="Folder2")
        nested_child = await create_test_folder(
            db_session, user, parent=folder1, name="NestedChild"
        )
        await db_session.commit()

        response = await test_client.get("/folders", params={"owner_id": str(user.id)})

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
        self, test_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test filtering folders by parent_id to get children."""
        user = await create_test_user(db_session)
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
            params={"owner_id": str(user.id), "parent_id": str(parent.id)},
        )

        assert response.status_code == 200
        data = response.json()
        folder_ids = [f["id"] for f in data]
        assert str(child1.id) in folder_ids
        assert str(child2.id) in folder_ids
        assert all(f["parent_id"] == str(parent.id) for f in data)

    @pytest.mark.asyncio
    async def test_list_folders_excludes_soft_deleted(
        self, test_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test that soft-deleted folders are not in list."""
        user = await create_test_user(db_session)
        active = await create_test_folder(db_session, user, name="Active")
        deleted = await create_test_folder(db_session, user, name="Deleted")
        await db_session.commit()

        await test_client.delete(f"/folders/{deleted.id}")

        response = await test_client.get("/folders", params={"owner_id": str(user.id)})

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
        self, test_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test getting a folder successfully."""
        user = await create_test_user(db_session)
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
    async def test_get_folder_not_found(self, test_client: AsyncClient) -> None:
        """Test getting non-existent folder returns 404."""
        import uuid

        response = await test_client.get(f"/folders/{uuid.uuid4()}")

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_folder_soft_deleted_returns_404(
        self, test_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test getting soft-deleted folder returns 404."""
        user = await create_test_user(db_session)
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
        self, test_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test getting folder tree with nested children."""
        user = await create_test_user(db_session)
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
        self, test_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test tree includes all descendant folders."""
        user = await create_test_user(db_session)
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
        self, test_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test soft-deleted children not included in tree."""
        user = await create_test_user(db_session)
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
        self, test_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test getting path from root to folder."""
        user = await create_test_user(db_session)
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
        self, test_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test path is in correct order (root to leaf)."""
        user = await create_test_user(db_session)
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
        self, test_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test root folder returns path with only itself."""
        user = await create_test_user(db_session)
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
        self, test_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test updating folder name successfully."""
        user = await create_test_user(db_session)
        folder = await create_test_folder(db_session, user, name="Old Name")
        await db_session.commit()

        update_data = {"name": "New Name"}
        response = await test_client.patch(f"/folders/{folder.id}", json=update_data)

        assert response.status_code == 200
        assert response.json()["name"] == "New Name"

    @pytest.mark.asyncio
    async def test_update_folder_description(
        self, test_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test updating folder description successfully."""
        user = await create_test_user(db_session)
        folder = await create_test_folder(
            db_session, user, description="Old desc"
        )
        await db_session.commit()

        update_data = {"description": "New description"}
        response = await test_client.patch(f"/folders/{folder.id}", json=update_data)

        assert response.status_code == 200
        assert response.json()["description"] == "New description"

    @pytest.mark.asyncio
    async def test_update_folder_duplicate_name_same_parent(
        self, test_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test duplicate name under same parent returns 409."""
        user = await create_test_user(db_session)
        parent = await create_test_folder(db_session, user, name="Parent")
        await create_test_folder(
            db_session, user, parent=parent, name="Existing"
        )
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
        self, test_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test moving folder to new parent successfully."""
        user = await create_test_user(db_session)
        old_parent = await create_test_folder(db_session, user, name="OldParent")
        new_parent = await create_test_folder(db_session, user, name="NewParent")
        folder = await create_test_folder(
            db_session, user, parent=old_parent, name="Folder"
        )
        await db_session.commit()

        move_data = {"parent_id": str(new_parent.id)}
        response = await test_client.patch(
            f"/folders/{folder.id}/move", json=move_data
        )

        assert response.status_code == 200
        assert response.json()["parent_id"] == str(new_parent.id)

    @pytest.mark.asyncio
    async def test_move_folder_to_root(
        self, test_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test moving folder to null parent (make it root)."""
        user = await create_test_user(db_session)
        parent = await create_test_folder(db_session, user, name="Parent")
        folder = await create_test_folder(
            db_session, user, parent=parent, name="Folder"
        )
        await db_session.commit()

        move_data = {"parent_id": None}
        response = await test_client.patch(
            f"/folders/{folder.id}/move", json=move_data
        )

        assert response.status_code == 200
        assert response.json()["parent_id"] is None

    @pytest.mark.asyncio
    async def test_move_folder_circular_reference(
        self, test_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test circular reference (move to own child) returns 400."""
        user = await create_test_user(db_session)
        parent = await create_test_folder(db_session, user, name="Parent")
        child = await create_test_folder(
            db_session, user, parent=parent, name="Child"
        )
        await db_session.commit()

        move_data = {"parent_id": str(child.id)}
        response = await test_client.patch(
            f"/folders/{parent.id}/move", json=move_data
        )

        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_move_folder_nonexistent_parent(
        self, test_client: AsyncClient
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
        self, test_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test soft deleting folder successfully."""
        user = await create_test_user(db_session)
        folder = await create_test_folder(db_session, user)
        await db_session.commit()

        response = await test_client.delete(f"/folders/{folder.id}")

        assert response.status_code == 204
        await db_session.refresh(folder)
        assert folder.deleted_at is not None

    @pytest.mark.asyncio
    async def test_soft_delete_folder_cascades_to_children(
        self, test_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test child folders cascade soft-deleted."""
        user = await create_test_user(db_session)
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
        self, test_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test folder deletion cascades to assessments."""
        user = await create_test_user(db_session)
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
        self, test_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test folder deletion cascades to assessment templates."""
        user = await create_test_user(db_session)
        folder = await create_test_folder(db_session, user, name="Folder")
        template1 = await create_test_assessment_template(db_session, user, folder=folder)
        template2 = await create_test_assessment_template(db_session, user, folder=folder)
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
        self, test_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test deletion works for deeply nested hierarchies."""
        user = await create_test_user(db_session)

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
    async def test_soft_delete_folder_not_found(self, test_client: AsyncClient) -> None:
        """Test soft deleting non-existent folder returns 404."""
        import uuid

        response = await test_client.delete(f"/folders/{uuid.uuid4()}")

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_cannot_delete_root_folder(
        self, test_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test that deleting root folder returns 403 Forbidden."""
        user = await create_test_user(db_session)
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
        self, test_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test getting folder with contents successfully."""
        user = await create_test_user(db_session)
        folder = await create_test_folder(
            db_session, user, name="Test Folder", description="Test desc"
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

    @pytest.mark.asyncio
    async def test_get_folder_contents_empty_folder(
        self, test_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test getting folder with no contents returns empty lists."""
        user = await create_test_user(db_session)
        folder = await create_test_folder(db_session, user, name="Empty Folder")
        await db_session.commit()

        response = await test_client.get(f"/folders/{folder.id}/contents")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(folder.id)
        assert data["assessments"] == []
        assert data["assessment_templates"] == []

    @pytest.mark.asyncio
    async def test_get_folder_contents_not_found(
        self, test_client: AsyncClient
    ) -> None:
        """Test getting non-existent folder returns 404."""
        import uuid

        response = await test_client.get(f"/folders/{uuid.uuid4()}/contents")

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_folder_contents_soft_deleted_folder_returns_404(
        self, test_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test getting soft-deleted folder returns 404."""
        user = await create_test_user(db_session)
        folder = await create_test_folder(db_session, user)
        await create_test_assessment(db_session, user, folder=folder)
        await db_session.commit()

        await test_client.delete(f"/folders/{folder.id}")
        response = await test_client.get(f"/folders/{folder.id}/contents")

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_folder_contents_excludes_soft_deleted_assessments(
        self, test_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test soft-deleted assessments are not included in contents."""
        user = await create_test_user(db_session)
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
        self, test_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test soft-deleted templates are not included in contents."""
        user = await create_test_user(db_session)
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
    async def test_get_folder_contents_returns_complete_objects(
        self, test_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test assessments and templates have complete fields."""
        user = await create_test_user(db_session)
        folder = await create_test_folder(db_session, user)
        assessment = await create_test_assessment(
            db_session,
            user,
            folder=folder,
            title="Test Assessment",
            description="Test description",
        )
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

        # Verify assessment has all required fields
        assessment_data = data["assessments"][0]
        assert assessment_data["id"] == str(assessment.id)
        assert assessment_data["title"] == "Test Assessment"
        assert assessment_data["description"] == "Test description"
        assert assessment_data["owner_id"] == str(user.id)
        assert assessment_data["folder_id"] == str(folder.id)
        assert "created_at" in assessment_data
        assert "updated_at" in assessment_data

        # Verify template has all required fields
        template_data = data["assessment_templates"][0]
        assert template_data["id"] == str(template.id)
        assert template_data["title"] == "Test Template"
        assert template_data["description"] == "Template desc"
        assert template_data["owner_id"] == str(user.id)
        assert template_data["folder_id"] == str(folder.id)
        assert "created_at" in template_data
        assert "updated_at" in template_data
