"""Integration tests for generic collaborator endpoints."""

from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from edcraft_backend.models.enums import CollaboratorRole, ResourceType
from edcraft_backend.models.folder import Folder
from edcraft_backend.models.resource_collaborator import ResourceCollaborator
from edcraft_backend.models.user import User
from tests.factories import (
    create_collaborator,
    create_test_assessment,
    create_test_assessment_template,
    create_test_question_bank,
    create_test_question_template_bank,
    create_test_user,
)

# ---------------------------------------------------------------------------
# Parametrize helpers
# ---------------------------------------------------------------------------

# (resource_path_segment, factory_fn, resource_type)
RESOURCE_PARAMS = [
    pytest.param(
        "assessments", create_test_assessment, ResourceType.ASSESSMENT, id="assessments"
    ),
    pytest.param(
        "question-banks",
        create_test_question_bank,
        ResourceType.QUESTION_BANK,
        id="question-banks",
    ),
    pytest.param(
        "question-template-banks",
        create_test_question_template_bank,
        ResourceType.QUESTION_TEMPLATE_BANK,
        id="question-template-banks",
    ),
    pytest.param(
        "assessment-templates",
        create_test_assessment_template,
        ResourceType.ASSESSMENT_TEMPLATE,
        id="assessment-templates",
    ),
]


@pytest.mark.integration
@pytest.mark.collaborators
class TestAddCollaborator:
    """Tests for POST /{resource_path}/{id}/collaborators."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("path,factory,rtype", RESOURCE_PARAMS)
    async def test_owner_can_add_editor(
        self,
        path: str,
        factory: Any,
        rtype: ResourceType,
        test_client: AsyncClient,
        db_session: AsyncSession,
        user: User,
    ) -> None:
        resource = await factory(db_session, user)
        await db_session.commit()

        new_user = await create_test_user(
            db_session, email=f"add_editor_{path}@test.com"
        )
        await db_session.commit()

        response = await test_client.post(
            f"/{path}/{resource.id}/collaborators",
            json={"email": new_user.email, "role": "editor"},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["user_email"] == new_user.email
        assert data["role"] == "editor"

    @pytest.mark.asyncio
    @pytest.mark.parametrize("path,factory,rtype", RESOURCE_PARAMS)
    async def test_editor_can_add_viewer(
        self,
        path: str,
        factory: Any,
        rtype: ResourceType,
        test_client: AsyncClient,
        db_session: AsyncSession,
        user: User,
    ) -> None:
        owner = await create_test_user(
            db_session, email=f"owner_editor_add_{path}@test.com"
        )
        resource = await factory(db_session, owner)
        await db_session.commit()

        await create_collaborator(
            db_session, rtype, resource.id, user, CollaboratorRole.EDITOR
        )
        new_user = await create_test_user(
            db_session, email=f"viewer_added_by_editor_{path}@test.com"
        )
        await db_session.commit()

        response = await test_client.post(
            f"/{path}/{resource.id}/collaborators",
            json={"email": new_user.email, "role": "viewer"},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["user_email"] == new_user.email
        assert data["role"] == "viewer"

    @pytest.mark.asyncio
    @pytest.mark.parametrize("path,factory,rtype", RESOURCE_PARAMS)
    async def test_viewer_cannot_add_returns_403(
        self,
        path: str,
        factory: Any,
        rtype: ResourceType,
        test_client: AsyncClient,
        db_session: AsyncSession,
        user: User,
    ) -> None:
        owner = await create_test_user(
            db_session, email=f"owner_viewer_add_{path}@test.com"
        )
        resource = await factory(db_session, owner)
        await db_session.commit()

        await create_collaborator(
            db_session, rtype, resource.id, user, CollaboratorRole.VIEWER
        )
        new_user = await create_test_user(
            db_session, email=f"blocked_add_{path}@test.com"
        )
        await db_session.commit()

        response = await test_client.post(
            f"/{path}/{resource.id}/collaborators",
            json={"email": new_user.email, "role": "viewer"},
        )

        assert response.status_code == 403

    @pytest.mark.asyncio
    @pytest.mark.parametrize("path,factory,rtype", RESOURCE_PARAMS)
    async def test_non_collaborator_cannot_add_returns_403(
        self,
        path: str,
        factory: Any,
        rtype: ResourceType,
        test_client: AsyncClient,
        db_session: AsyncSession,
        user: User,
    ) -> None:
        other_owner = await create_test_user(
            db_session, email=f"other_owner_nadd_{path}@test.com"
        )
        resource = await factory(db_session, other_owner)
        await db_session.commit()

        response = await test_client.post(
            f"/{path}/{resource.id}/collaborators",
            json={"email": user.email, "role": "editor"},
        )

        assert response.status_code == 403

    @pytest.mark.asyncio
    @pytest.mark.parametrize("path,factory,rtype", RESOURCE_PARAMS)
    async def test_add_owner_role_returns_422(
        self,
        path: str,
        factory: Any,
        rtype: ResourceType,
        test_client: AsyncClient,
        db_session: AsyncSession,
        user: User,
    ) -> None:
        resource = await factory(db_session, user)
        new_user = await create_test_user(
            db_session, email=f"owner_assign_{path}@test.com"
        )
        await db_session.commit()

        response = await test_client.post(
            f"/{path}/{resource.id}/collaborators",
            json={"email": new_user.email, "role": "owner"},
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    @pytest.mark.parametrize("path,factory,rtype", RESOURCE_PARAMS)
    async def test_unknown_email_returns_404(
        self,
        path: str,
        factory: Any,
        rtype: ResourceType,
        test_client: AsyncClient,
        db_session: AsyncSession,
        user: User,
    ) -> None:
        resource = await factory(db_session, user)
        await db_session.commit()

        response = await test_client.post(
            f"/{path}/{resource.id}/collaborators",
            json={"email": "ghost@unknown.example", "role": "editor"},
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    @pytest.mark.parametrize("path,factory,rtype", RESOURCE_PARAMS)
    async def test_duplicate_collaborator_returns_409(
        self,
        path: str,
        factory: Any,
        rtype: ResourceType,
        test_client: AsyncClient,
        db_session: AsyncSession,
        user: User,
    ) -> None:
        resource = await factory(db_session, user)
        new_user = await create_test_user(
            db_session, email=f"dup_collab_{path}@test.com"
        )
        await db_session.commit()

        # First add succeeds
        await test_client.post(
            f"/{path}/{resource.id}/collaborators",
            json={"email": new_user.email, "role": "editor"},
        )
        # Second add is a duplicate
        response = await test_client.post(
            f"/{path}/{resource.id}/collaborators",
            json={"email": new_user.email, "role": "editor"},
        )

        assert response.status_code == 409


@pytest.mark.integration
@pytest.mark.collaborators
class TestListCollaborators:
    """Tests for GET /{resource_path}/{id}/collaborators."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("path,factory,rtype", RESOURCE_PARAMS)
    async def test_owner_can_list(
        self,
        path: str,
        factory: Any,
        rtype: ResourceType,
        test_client: AsyncClient,
        db_session: AsyncSession,
        user: User,
    ) -> None:
        resource = await factory(db_session, user)
        await db_session.commit()

        response = await test_client.get(f"/{path}/{resource.id}/collaborators")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        roles = [c["role"] for c in data]
        assert "owner" in roles

    @pytest.mark.asyncio
    @pytest.mark.parametrize("path,factory,rtype", RESOURCE_PARAMS)
    async def test_editor_can_list(
        self,
        path: str,
        factory: Any,
        rtype: ResourceType,
        test_client: AsyncClient,
        db_session: AsyncSession,
        user: User,
    ) -> None:
        owner = await create_test_user(db_session, email=f"owner_list_{path}@test.com")
        resource = await factory(db_session, owner)
        await db_session.commit()

        await create_collaborator(
            db_session, rtype, resource.id, user, CollaboratorRole.EDITOR
        )
        await db_session.commit()

        response = await test_client.get(f"/{path}/{resource.id}/collaborators")

        assert response.status_code == 200

    @pytest.mark.asyncio
    @pytest.mark.parametrize("path,factory,rtype", RESOURCE_PARAMS)
    async def test_viewer_cannot_list_returns_403(
        self,
        path: str,
        factory: Any,
        rtype: ResourceType,
        test_client: AsyncClient,
        db_session: AsyncSession,
        user: User,
    ) -> None:
        owner = await create_test_user(
            db_session, email=f"owner_viewer_list_{path}@test.com"
        )
        resource = await factory(db_session, owner)
        await db_session.commit()

        await create_collaborator(
            db_session, rtype, resource.id, user, CollaboratorRole.VIEWER
        )
        await db_session.commit()

        response = await test_client.get(f"/{path}/{resource.id}/collaborators")

        assert response.status_code == 403

    @pytest.mark.asyncio
    @pytest.mark.parametrize("path,factory,rtype", RESOURCE_PARAMS)
    async def test_non_collaborator_cannot_list_returns_403(
        self,
        path: str,
        factory: Any,
        rtype: ResourceType,
        test_client: AsyncClient,
        db_session: AsyncSession,
        user: User,
    ) -> None:
        other_owner = await create_test_user(
            db_session, email=f"other_owner_list_{path}@test.com"
        )
        resource = await factory(db_session, other_owner)
        await db_session.commit()

        response = await test_client.get(f"/{path}/{resource.id}/collaborators")

        assert response.status_code == 403


@pytest.mark.integration
@pytest.mark.collaborators
class TestUpdateCollaboratorRole:
    """Tests for PATCH /{resource_path}/{id}/collaborators/{collaborator_id}."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("path,factory,rtype", RESOURCE_PARAMS)
    async def test_owner_can_update_role(
        self,
        path: str,
        factory: Any,
        rtype: ResourceType,
        test_client: AsyncClient,
        db_session: AsyncSession,
        user: User,
    ) -> None:
        resource = await factory(db_session, user)
        editor_user = await create_test_user(
            db_session, email=f"editor_update_{path}@test.com"
        )
        await db_session.commit()

        add_resp = await test_client.post(
            f"/{path}/{resource.id}/collaborators",
            json={"email": editor_user.email, "role": "editor"},
        )
        collab_id = add_resp.json()["id"]

        response = await test_client.patch(
            f"/{path}/{resource.id}/collaborators/{collab_id}",
            json={"role": "viewer"},
        )

        assert response.status_code == 200
        assert response.json()["role"] == "viewer"

    @pytest.mark.asyncio
    @pytest.mark.parametrize("path,factory,rtype", RESOURCE_PARAMS)
    async def test_editor_can_change_viewer_to_editor(
        self,
        path: str,
        factory: Any,
        rtype: ResourceType,
        test_client: AsyncClient,
        db_session: AsyncSession,
        user: User,
    ) -> None:
        owner = await create_test_user(
            db_session, email=f"owner_editor_prom_{path}@test.com"
        )
        resource = await factory(db_session, owner)
        await db_session.commit()

        await create_collaborator(
            db_session, rtype, resource.id, user, CollaboratorRole.EDITOR
        )
        viewer_user = await create_test_user(
            db_session, email=f"viewer_promoted_{path}@test.com"
        )
        viewer_collab = await create_collaborator(
            db_session, rtype, resource.id, viewer_user, CollaboratorRole.VIEWER
        )
        await db_session.commit()

        response = await test_client.patch(
            f"/{path}/{resource.id}/collaborators/{viewer_collab.id}",
            json={"role": "editor"},
        )

        assert response.status_code == 200
        assert response.json()["role"] == "editor"

    @pytest.mark.asyncio
    @pytest.mark.parametrize("path,factory,rtype", RESOURCE_PARAMS)
    async def test_editor_cannot_assign_owner_returns_400(
        self,
        path: str,
        factory: Any,
        rtype: ResourceType,
        test_client: AsyncClient,
        db_session: AsyncSession,
        user: User,
    ) -> None:
        owner = await create_test_user(
            db_session, email=f"owner_editor_owner_{path}@test.com"
        )
        resource = await factory(db_session, owner)
        await db_session.commit()

        await create_collaborator(
            db_session, rtype, resource.id, user, CollaboratorRole.EDITOR
        )
        viewer_user = await create_test_user(
            db_session, email=f"viewer_to_owner_{path}@test.com"
        )
        viewer_collab = await create_collaborator(
            db_session, rtype, resource.id, viewer_user, CollaboratorRole.VIEWER
        )
        await db_session.commit()

        response = await test_client.patch(
            f"/{path}/{resource.id}/collaborators/{viewer_collab.id}",
            json={"role": "owner"},
        )

        assert response.status_code == 400

    @pytest.mark.asyncio
    @pytest.mark.parametrize("path,factory,rtype", RESOURCE_PARAMS)
    async def test_cannot_directly_change_owner_role_returns_400(
        self,
        path: str,
        factory: Any,
        rtype: ResourceType,
        test_client: AsyncClient,
        db_session: AsyncSession,
        user: User,
    ) -> None:
        resource = await factory(db_session, user)
        await db_session.commit()

        owner_collab = (
            await db_session.execute(
                select(ResourceCollaborator).where(
                    ResourceCollaborator.resource_id == resource.id,
                    ResourceCollaborator.user_id == user.id,
                )
            )
        ).scalar_one()

        response = await test_client.patch(
            f"/{path}/{resource.id}/collaborators/{owner_collab.id}",
            json={"role": "viewer"},
        )

        assert response.status_code == 400

    @pytest.mark.asyncio
    @pytest.mark.parametrize("path,factory,rtype", RESOURCE_PARAMS)
    async def test_ownership_transfer(
        self,
        path: str,
        factory: Any,
        rtype: ResourceType,
        test_client: AsyncClient,
        db_session: AsyncSession,
        user: User,
    ) -> None:
        resource = await factory(db_session, user)
        future_owner = await create_test_user(
            db_session, email=f"future_owner_transfer_{path}@test.com"
        )
        await db_session.commit()

        add_resp = await test_client.post(
            f"/{path}/{resource.id}/collaborators",
            json={"email": future_owner.email, "role": "editor"},
        )
        collab_id = add_resp.json()["id"]

        response = await test_client.patch(
            f"/{path}/{resource.id}/collaborators/{collab_id}",
            json={"role": "owner"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["role"] == "owner"
        assert data["user_email"] == future_owner.email

        # Original owner should now be editor
        collabs_resp = await test_client.get(f"/{path}/{resource.id}/collaborators")
        original = next(c for c in collabs_resp.json() if c["user_email"] == user.email)
        assert original["role"] == "editor"

        # Resource should be in new owner's root folder
        await db_session.refresh(resource)
        new_owner_root = (
            await db_session.execute(
                select(Folder).where(
                    Folder.owner_id == future_owner.id,
                    Folder.parent_id.is_(None),
                )
            )
        ).scalar_one()
        assert resource.folder_id == new_owner_root.id


@pytest.mark.integration
@pytest.mark.collaborators
class TestRemoveCollaborator:
    """Tests for DELETE /{resource_path}/{id}/collaborators/{collaborator_id}."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("path,factory,rtype", RESOURCE_PARAMS)
    async def test_owner_can_remove_non_owner(
        self,
        path: str,
        factory: Any,
        rtype: ResourceType,
        test_client: AsyncClient,
        db_session: AsyncSession,
        user: User,
    ) -> None:
        resource = await factory(db_session, user)
        editor_user = await create_test_user(
            db_session, email=f"editor_remove_{path}@test.com"
        )
        await db_session.commit()

        add_resp = await test_client.post(
            f"/{path}/{resource.id}/collaborators",
            json={"email": editor_user.email, "role": "editor"},
        )
        collab_id = add_resp.json()["id"]

        response = await test_client.delete(
            f"/{path}/{resource.id}/collaborators/{collab_id}"
        )

        assert response.status_code == 204

    @pytest.mark.asyncio
    @pytest.mark.parametrize("path,factory,rtype", RESOURCE_PARAMS)
    async def test_editor_can_remove_viewer(
        self,
        path: str,
        factory: Any,
        rtype: ResourceType,
        test_client: AsyncClient,
        db_session: AsyncSession,
        user: User,
    ) -> None:
        owner = await create_test_user(
            db_session, email=f"owner_editor_remove_{path}@test.com"
        )
        resource = await factory(db_session, owner)
        await db_session.commit()

        await create_collaborator(
            db_session, rtype, resource.id, user, CollaboratorRole.EDITOR
        )
        viewer_user = await create_test_user(
            db_session, email=f"viewer_removed_{path}@test.com"
        )
        viewer_collab = await create_collaborator(
            db_session, rtype, resource.id, viewer_user, CollaboratorRole.VIEWER
        )
        await db_session.commit()

        response = await test_client.delete(
            f"/{path}/{resource.id}/collaborators/{viewer_collab.id}"
        )

        assert response.status_code == 204

    @pytest.mark.asyncio
    @pytest.mark.parametrize("path,factory,rtype", RESOURCE_PARAMS)
    async def test_cannot_remove_owner_returns_400(
        self,
        path: str,
        factory: Any,
        rtype: ResourceType,
        test_client: AsyncClient,
        db_session: AsyncSession,
        user: User,
    ) -> None:
        resource = await factory(db_session, user)
        await db_session.commit()

        owner_collab = (
            await db_session.execute(
                select(ResourceCollaborator).where(
                    ResourceCollaborator.resource_id == resource.id,
                    ResourceCollaborator.user_id == user.id,
                )
            )
        ).scalar_one()

        response = await test_client.delete(
            f"/{path}/{resource.id}/collaborators/{owner_collab.id}"
        )

        assert response.status_code == 400

    @pytest.mark.asyncio
    @pytest.mark.parametrize("path,factory,rtype", RESOURCE_PARAMS)
    async def test_collaborator_not_found_returns_404(
        self,
        path: str,
        factory: Any,
        rtype: ResourceType,
        test_client: AsyncClient,
        db_session: AsyncSession,
        user: User,
    ) -> None:
        resource = await factory(db_session, user)
        await db_session.commit()

        import uuid

        response = await test_client.delete(
            f"/{path}/{resource.id}/collaborators/{uuid.uuid4()}"
        )

        assert response.status_code == 404
