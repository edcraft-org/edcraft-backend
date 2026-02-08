"""Integration tests for User API endpoints."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from edcraft_backend.models.user import User
from tests.factories import create_test_user


@pytest.mark.integration
@pytest.mark.users
class TestGetUser:
    """Tests for GET /users/me endpoint."""

    @pytest.mark.asyncio
    async def test_get_user_success(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test getting the current authenticated user successfully."""
        response = await test_client.get("/users/me")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(user.id)
        assert data["email"] == user.email

    @pytest.mark.asyncio
    async def test_get_user_without_auth(self, test_client: AsyncClient) -> None:
        """Test getting user without authentication returns 401."""
        response = await test_client.get("/users/me")

        assert response.status_code == 401


@pytest.mark.integration
@pytest.mark.users
class TestUpdateUser:
    """Tests for PATCH /users/me endpoint."""

    @pytest.mark.asyncio
    async def test_update_user_email_success(
        self, test_client: AsyncClient, user: User
    ) -> None:
        """Test updating user email successfully."""

        update_data = {"email": "newemail@example.com"}
        response = await test_client.patch("/users/me", json=update_data)

        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "newemail@example.com"

    @pytest.mark.asyncio
    async def test_update_user_name_success(
        self, test_client: AsyncClient, user: User
    ) -> None:
        """Test updating user name successfully."""
        update_data = {"name": "newname"}
        response = await test_client.patch("/users/me", json=update_data)

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "newname"

    @pytest.mark.asyncio
    async def test_update_user_duplicate_email(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test updating user with duplicate email returns 409 Conflict."""
        await create_test_user(db_session, email="taken@example.com")
        await db_session.commit()

        update_data = {"email": "taken@example.com"}
        response = await test_client.patch("/users/me", json=update_data)

        assert response.status_code == 409

    @pytest.mark.asyncio
    async def test_update_user_without_auth(self, test_client: AsyncClient) -> None:
        """Test updating user without authentication returns 401."""
        update_data = {"email": "new@example.com"}
        response = await test_client.patch("/users/me", json=update_data)

        assert response.status_code == 401


@pytest.mark.integration
@pytest.mark.users
class TestSoftDeleteUser:
    """Tests for DELETE /users/me endpoint."""

    @pytest.mark.asyncio
    async def test_soft_delete_user_success(
        self, test_client: AsyncClient, db_session: AsyncSession, user: User
    ) -> None:
        """Test soft deleting the current user and their root folder successfully."""
        from tests.factories import get_user_root_folder

        root_folder = await get_user_root_folder(db_session, user)

        response = await test_client.delete("/users/me")

        assert response.status_code == 204

        # Verify user has deleted_at timestamp
        await db_session.refresh(user)
        assert user.deleted_at is not None

        # Verify root folder has deleted_at timestamp
        await db_session.refresh(root_folder)
        assert root_folder.deleted_at is not None

    @pytest.mark.asyncio
    async def test_soft_delete_user_without_auth(
        self, test_client: AsyncClient
    ) -> None:
        """Test soft deleting user without authentication returns 401."""
        response = await test_client.delete("/users/me")

        assert response.status_code == 401


@pytest.mark.integration
@pytest.mark.users
class TestGetUserRootFolder:
    """Tests for GET /users/me/root-folder endpoint."""

    @pytest.mark.asyncio
    async def test_get_root_folder_success(
        self, test_client: AsyncClient, user: User
    ) -> None:
        """Test getting root folder for the current authenticated user."""
        response = await test_client.get("/users/me/root-folder")

        assert response.status_code == 200
        data = response.json()
        assert data["owner_id"] == str(user.id)
        assert data["parent_id"] is None
        assert data["name"] == "My Projects"

    @pytest.mark.asyncio
    async def test_get_root_folder_without_auth(self, test_client: AsyncClient) -> None:
        """Test getting root folder without authentication returns 401."""
        response = await test_client.get("/users/me/root-folder")

        assert response.status_code == 401
