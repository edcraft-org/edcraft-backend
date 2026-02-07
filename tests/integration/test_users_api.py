"""Integration tests for User API endpoints."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.factories import create_test_user


@pytest.mark.integration
@pytest.mark.users
class TestCreateUser:
    """Tests for POST /users endpoint."""

    @pytest.mark.asyncio
    async def test_create_user_success(self, test_client: AsyncClient) -> None:
        """Test successful user creation with valid data."""
        user_data = {
            "email": "newuser@example.com",
            "name": "newuser",
        }
        response = await test_client.post("/users", json=user_data)

        assert response.status_code == 201
        data = response.json()
        assert data["email"] == user_data["email"]
        assert data["name"] == user_data["name"]
        assert "id" in data
        assert "created_at" in data
        assert "updated_at" in data

    @pytest.mark.asyncio
    async def test_create_user_duplicate_email(
        self, test_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test user creation with duplicate email returns 409 Conflict."""
        # Create existing user
        await create_test_user(db_session, email="existing@example.com")
        await db_session.commit()

        # Try to create user with duplicate email
        user_data = {
            "email": "existing@example.com",
            "name": "newuser",
        }
        response = await test_client.post("/users", json=user_data)

        assert response.status_code == 409
        assert "already exists" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_create_user_invalid_email(self, test_client: AsyncClient) -> None:
        """Test user creation with invalid email format returns 422 Validation Error."""
        user_data = {
            "email": "not-an-email",
            "name": "testuser",
        }
        response = await test_client.post("/users", json=user_data)

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_user_creation_creates_root_folder(
        self, test_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test that creating a user automatically creates their root folder."""
        from sqlalchemy import select

        from edcraft_backend.models.folder import Folder

        user_data = {"email": "newuserauto@example.com", "name": "newuserauto"}
        response = await test_client.post("/users", json=user_data)
        assert response.status_code == 201
        user_id = response.json()["id"]

        # Verify root folder exists in database
        result = await db_session.execute(
            select(Folder).where(
                Folder.owner_id == user_id,
                Folder.parent_id.is_(None)
            )
        )
        root_folder = result.scalar_one_or_none()
        assert root_folder is not None
        assert root_folder.name == "My Projects"


@pytest.mark.integration
@pytest.mark.users
class TestListUsers:
    """Tests for GET /users endpoint."""

    @pytest.mark.asyncio
    async def test_list_users_success(
        self, test_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test listing all users successfully."""
        # Create test users
        _user1 = await create_test_user(db_session, email="user1@example.com")
        _user2 = await create_test_user(db_session, email="user2@example.com")
        await db_session.commit()

        response = await test_client.get("/users")

        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 2
        emails = [user["email"] for user in data]
        assert "user1@example.com" in emails
        assert "user2@example.com" in emails

    @pytest.mark.asyncio
    async def test_list_users_excludes_soft_deleted(
        self, test_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test that soft-deleted users are not in list."""
        # Create users
        _user1 = await create_test_user(db_session, email="active@example.com")
        user2 = await create_test_user(db_session, email="deleted@example.com")
        await db_session.commit()

        # Soft delete user2
        await test_client.delete(f"/users/{user2.id}")

        # List users
        response = await test_client.get("/users")

        assert response.status_code == 200
        data = response.json()
        emails = [user["email"] for user in data]
        assert "active@example.com" in emails
        assert "deleted@example.com" not in emails

    @pytest.mark.asyncio
    async def test_list_users_empty(self, test_client: AsyncClient) -> None:
        """Test listing users when no users exist returns empty list."""
        response = await test_client.get("/users")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


@pytest.mark.integration
@pytest.mark.users
class TestGetUser:
    """Tests for GET /users/{user_id} endpoint."""

    @pytest.mark.asyncio
    async def test_get_user_success(
        self, test_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test getting a user successfully with valid ID."""
        user = await create_test_user(db_session, email="getme@example.com")
        await db_session.commit()

        response = await test_client.get(f"/users/{user.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(user.id)
        assert data["email"] == "getme@example.com"

    @pytest.mark.asyncio
    async def test_get_user_not_found(self, test_client: AsyncClient) -> None:
        """Test getting non-existent user returns 404 Not Found."""
        import uuid

        non_existent_id = uuid.uuid4()
        response = await test_client.get(f"/users/{non_existent_id}")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_get_user_soft_deleted_returns_404(
        self, test_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test getting soft-deleted user returns 404 Not Found."""
        user = await create_test_user(db_session, email="deleted@example.com")
        await db_session.commit()

        # Soft delete the user
        await test_client.delete(f"/users/{user.id}")

        # Try to get the soft-deleted user
        response = await test_client.get(f"/users/{user.id}")

        assert response.status_code == 404


@pytest.mark.integration
@pytest.mark.users
class TestUpdateUser:
    """Tests for PATCH /users/{user_id} endpoint."""

    @pytest.mark.asyncio
    async def test_update_user_email_success(
        self, test_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test updating user email successfully."""
        user = await create_test_user(db_session, email="old@example.com")
        await db_session.commit()

        update_data = {"email": "new@example.com"}
        response = await test_client.patch(f"/users/{user.id}", json=update_data)

        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "new@example.com"

    @pytest.mark.asyncio
    async def test_update_user_name_success(
        self, test_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test updating user name successfully."""
        user = await create_test_user(db_session, name="oldname")
        await db_session.commit()

        update_data = {"name": "newname"}
        response = await test_client.patch(f"/users/{user.id}", json=update_data)

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "newname"

    @pytest.mark.asyncio
    async def test_update_user_duplicate_email(
        self, test_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test updating user with duplicate email returns 409 Conflict."""
        _user1 = await create_test_user(db_session, email="user1@example.com")
        user2 = await create_test_user(db_session, email="user2@example.com")
        await db_session.commit()

        # Try to update user2 with user1's email
        update_data = {"email": "user1@example.com"}
        response = await test_client.patch(f"/users/{user2.id}", json=update_data)

        assert response.status_code == 409

    @pytest.mark.asyncio
    async def test_update_user_not_found(self, test_client: AsyncClient) -> None:
        """Test updating non-existent user returns 404 Not Found."""
        import uuid

        non_existent_id = uuid.uuid4()
        update_data = {"email": "new@example.com"}
        response = await test_client.patch(f"/users/{non_existent_id}", json=update_data)

        assert response.status_code == 404


@pytest.mark.integration
@pytest.mark.users
class TestSoftDeleteUser:
    """Tests for DELETE /users/{user_id} endpoint."""

    @pytest.mark.asyncio
    async def test_soft_delete_user_success(
        self, test_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test soft deleting user successfully."""
        user = await create_test_user(db_session, email="deleteme@example.com")
        await db_session.commit()

        response = await test_client.delete(f"/users/{user.id}")

        assert response.status_code == 204

        # Verify user has deleted_at timestamp
        await db_session.refresh(user)
        assert user.deleted_at is not None

    @pytest.mark.asyncio
    async def test_soft_delete_user_not_in_list(
        self, test_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test soft-deleted user not in list results."""
        user = await create_test_user(db_session, email="deleted@example.com")
        await db_session.commit()

        # Soft delete user
        await test_client.delete(f"/users/{user.id}")

        # List users
        response = await test_client.get("/users")

        assert response.status_code == 200
        data = response.json()
        user_ids = [u["id"] for u in data]
        assert str(user.id) not in user_ids

    @pytest.mark.asyncio
    async def test_soft_delete_user_not_found(self, test_client: AsyncClient) -> None:
        """Test soft deleting non-existent user returns 404 Not Found."""
        import uuid

        non_existent_id = uuid.uuid4()
        response = await test_client.delete(f"/users/{non_existent_id}")

        assert response.status_code == 404


@pytest.mark.integration
@pytest.mark.users
class TestHardDeleteUser:
    """Tests for DELETE /users/{user_id}/hard endpoint."""

    @pytest.mark.asyncio
    async def test_hard_delete_user_success(
        self, test_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test hard deleting user successfully."""
        user = await create_test_user(db_session, email="harddelete@example.com")
        user_id = user.id
        await db_session.commit()

        response = await test_client.delete(f"/users/{user_id}/hard")

        assert response.status_code == 204

        # Verify user no longer exists
        from sqlalchemy import select

        from edcraft_backend.models.user import User

        result = await db_session.execute(select(User).where(User.id == user_id))
        deleted_user = result.scalar_one_or_none()
        assert deleted_user is None

    @pytest.mark.asyncio
    async def test_hard_delete_user_cascades_to_folders(
        self, test_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test hard deleting user cascades to user's folders."""
        from tests.factories import create_test_folder

        user = await create_test_user(db_session, email="cascade@example.com")
        folder = await create_test_folder(db_session, owner=user, name="Test Folder")
        folder_id = folder.id
        await db_session.commit()

        # Hard delete user
        response = await test_client.delete(f"/users/{user.id}/hard")
        assert response.status_code == 204

        # Verify folder was also deleted
        from sqlalchemy import select

        from edcraft_backend.models.folder import Folder

        result = await db_session.execute(select(Folder).where(Folder.id == folder_id))
        deleted_folder = result.scalar_one_or_none()
        assert deleted_folder is None

    @pytest.mark.asyncio
    async def test_hard_delete_user_not_found(self, test_client: AsyncClient) -> None:
        """Test hard deleting non-existent user returns 404 Not Found."""
        import uuid

        non_existent_id = uuid.uuid4()
        response = await test_client.delete(f"/users/{non_existent_id}/hard")

        assert response.status_code == 404


@pytest.mark.integration
@pytest.mark.users
class TestGetUserRootFolder:
    """Tests for GET /users/{user_id}/root-folder endpoint."""

    @pytest.mark.asyncio
    async def test_get_root_folder_success(
        self, test_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test getting root folder for existing user."""
        user = await create_test_user(db_session, email="roottest@example.com", name="roottest")
        await db_session.commit()

        response = await test_client.get(f"/users/{user.id}/root-folder")

        assert response.status_code == 200
        data = response.json()
        assert data["owner_id"] == str(user.id)
        assert data["parent_id"] is None
        assert data["name"] == "My Projects"

    @pytest.mark.asyncio
    async def test_get_root_folder_user_not_found(
        self, test_client: AsyncClient
    ) -> None:
        """Test getting root folder for non-existent user returns 404."""
        import uuid

        response = await test_client.get(f"/users/{uuid.uuid4()}/root-folder")
        assert response.status_code == 404
