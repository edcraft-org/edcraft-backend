"""Integration tests for Auth API endpoints."""

from unittest.mock import AsyncMock, patch
from urllib.parse import parse_qs, urlparse

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from edcraft_backend.oauth.providers import OAuthUserInfo
from tests.factories import create_test_user
from tests.mocks import MockOAuthRegistry


@pytest.mark.integration
@pytest.mark.auth
class TestSignup:
    """Tests for POST /auth/signup endpoint."""

    @pytest.mark.asyncio
    async def test_signup_success(
        self, test_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test successful user signup with valid email and password."""
        from sqlalchemy import select

        from edcraft_backend.models.folder import Folder

        signup_data = {
            "email": "newuser@example.com",
            "password": "SecurePassword123!",
        }
        response = await test_client.post("/auth/signup", json=signup_data)

        assert response.status_code == 201
        data = response.json()
        assert data["email"] == signup_data["email"]
        assert "id" in data
        assert "name" in data and data["name"] == "newuser"
        assert "password" not in data
        assert "password_hash" not in data

        # Verify root folder was created during signup
        user_id = data["id"]
        result = await db_session.execute(
            select(Folder).where(Folder.owner_id == user_id, Folder.parent_id.is_(None))
        )
        root_folder = result.scalar_one_or_none()
        assert root_folder is not None
        assert root_folder.name == "My Projects"

    @pytest.mark.asyncio
    async def test_signup_duplicate_email(
        self, test_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test signup with duplicate email returns 409 Conflict."""
        # Create existing user with password
        await create_test_user(
            db_session,
            email="existing@example.com",
            password_hash="hashed_password",  # noqa S106
        )
        await db_session.commit()

        # Try to signup with duplicate email
        signup_data = {
            "email": "existing@example.com",
            "password": "SecurePassword123!",
        }
        response = await test_client.post("/auth/signup", json=signup_data)

        assert response.status_code == 409
        assert "already exists" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_signup_password_too_short(self, test_client: AsyncClient) -> None:
        """Test signup with password shorter than minimum length returns 422."""
        signup_data = {
            "email": "user@example.com",
            "password": "short",  # Less than 12 characters
        }
        response = await test_client.post("/auth/signup", json=signup_data)

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_signup_with_previously_deleted_email(
        self, test_client: AsyncClient
    ) -> None:
        """Test signup with an email belonging to a soft-deleted account succeeds."""
        signup_data = {
            "email": "reuse@example.com",
            "password": "SecurePassword123!",
        }

        # Create and delete the first account
        await test_client.post("/auth/signup", json=signup_data)
        await test_client.post("/auth/login", json=signup_data)
        await test_client.delete("/users/me")

        # Signup again with the same email
        response = await test_client.post("/auth/signup", json=signup_data)

        assert response.status_code == 201
        assert response.json()["email"] == signup_data["email"]

    @pytest.mark.asyncio
    async def test_signup_creates_root_folder(
        self, test_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test that creating a user automatically creates their root folder."""
        from sqlalchemy import select

        from edcraft_backend.models.folder import Folder

        user_data = {
            "email": "newuserauto@example.com",
            "password": "SecurePassword123!",
        }
        response = await test_client.post("/auth/signup", json=user_data)
        assert response.status_code == 201
        user_id = response.json()["id"]

        # Verify root folder exists in database
        result = await db_session.execute(
            select(Folder).where(Folder.owner_id == user_id, Folder.parent_id.is_(None))
        )
        root_folder = result.scalar_one_or_none()
        assert root_folder is not None
        assert root_folder.name == "My Projects"


@pytest.mark.integration
@pytest.mark.auth
class TestLogin:
    """Tests for POST /auth/login endpoint."""

    @pytest.mark.asyncio
    async def test_login_success(self, test_client: AsyncClient) -> None:
        """Test successful login with valid credentials."""
        # Create user via signup
        signup_data = {
            "email": "loginuser@example.com",
            "password": "SecurePassword123!",
        }
        await test_client.post("/auth/signup", json=signup_data)

        # Login with same credentials
        login_data = {
            "email": "loginuser@example.com",
            "password": "SecurePassword123!",
        }
        response = await test_client.post("/auth/login", json=login_data)

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"  # noqa S105
        assert "expires_in" in data

        # Verify cookies are set
        assert "access_token" in response.cookies
        assert "refresh_token" in response.cookies

    @pytest.mark.asyncio
    async def test_login_wrong_password(self, test_client: AsyncClient) -> None:
        """Test login with incorrect password returns 401 Unauthorized."""
        # Create user via signup
        signup_data = {
            "email": "user@example.com",
            "password": "CorrectPassword123!",
        }
        await test_client.post("/auth/signup", json=signup_data)

        # Try to login with wrong password
        login_data = {
            "email": "user@example.com",
            "password": "WrongPassword123!",
        }
        response = await test_client.post("/auth/login", json=login_data)

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_login_nonexistent_user(self, test_client: AsyncClient) -> None:
        """Test login with non-existent user returns 401 Unauthorized."""
        login_data = {
            "email": "nonexistent@example.com",
            "password": "SomePassword123!",
        }
        response = await test_client.post("/auth/login", json=login_data)

        assert response.status_code == 401


@pytest.mark.integration
@pytest.mark.auth
class TestRefreshToken:
    """Tests for POST /auth/refresh endpoint."""

    @pytest.mark.asyncio
    @pytest.mark.skip(
        reason="Refresh token test requires DB persistence across requests, "
        "which conflicts with transaction-based test isolation. "
        "TODO: Implement with custom fixture or mock token repository"
    )
    async def test_refresh_token_success(self, test_client: AsyncClient) -> None:
        """Test successful token refresh with valid refresh token."""
        # Create user and login
        signup_data = {
            "email": "refreshuser@example.com",
            "password": "SecurePassword123!",
        }
        await test_client.post("/auth/signup", json=signup_data)

        login_response = await test_client.post("/auth/login", json=signup_data)
        old_access_token = login_response.json()["access_token"]

        # Refresh token using cookies from login
        response = await test_client.post("/auth/refresh")

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"  # noqa S105
        assert "expires_in" in data

        # Verify new access token is different
        assert data["access_token"] != old_access_token

        # Verify cookies are updated
        assert "access_token" in response.cookies
        assert "refresh_token" in response.cookies

    @pytest.mark.asyncio
    async def test_refresh_token_missing(self, test_client: AsyncClient) -> None:
        """Test refresh without refresh token cookie returns 401."""
        response = await test_client.post("/auth/refresh")

        assert response.status_code == 401
        assert "missing" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_refresh_token_invalid(self, test_client: AsyncClient) -> None:
        """Test refresh with invalid refresh token returns 401."""
        # Set invalid refresh token cookie
        test_client.cookies.set("refresh_token", "invalid_token")

        response = await test_client.post("/auth/refresh")

        assert response.status_code == 401


@pytest.mark.integration
@pytest.mark.auth
class TestLogout:
    """Tests for POST /auth/logout endpoint."""

    @pytest.mark.asyncio
    async def test_logout_success(self, test_client: AsyncClient) -> None:
        """Test successful logout clears cookies."""
        # Create user and login
        signup_data = {
            "email": "logoutuser@example.com",
            "password": "SecurePassword123!",
        }
        await test_client.post("/auth/signup", json=signup_data)
        await test_client.post("/auth/login", json=signup_data)

        # Logout
        response = await test_client.post("/auth/logout")

        assert response.status_code == 204

        # Verify cookies are cleared (set to empty)
        cookies = response.headers.get_list("set-cookie")
        assert any("access_token" in cookie for cookie in cookies)
        assert any("refresh_token" in cookie for cookie in cookies)

    @pytest.mark.asyncio
    async def test_logout_without_auth(self, test_client: AsyncClient) -> None:
        """Test logout without authentication returns 401."""
        response = await test_client.post("/auth/logout")

        assert response.status_code == 401


@pytest.mark.integration
@pytest.mark.auth
class TestGetMe:
    """Tests for GET /auth/me endpoint."""

    @pytest.mark.asyncio
    async def test_get_me_success(self, test_client: AsyncClient) -> None:
        """Test getting authenticated user profile successfully."""
        # Create user and login
        signup_data = {
            "email": "meuser@example.com",
            "password": "SecurePassword123!",
        }
        signup_response = await test_client.post("/auth/signup", json=signup_data)
        await test_client.post("/auth/login", json=signup_data)

        # Get authenticated user profile
        response = await test_client.get("/auth/me")

        assert response.status_code == 200
        data = response.json()
        assert data["email"] == signup_data["email"]
        assert "id" in data
        assert "name" in data
        assert data["id"] == signup_response.json()["id"]

    @pytest.mark.asyncio
    async def test_get_me_without_auth(self, test_client: AsyncClient) -> None:
        """Test getting user profile without authentication returns 401."""
        response = await test_client.get("/auth/me")

        assert response.status_code == 401


@pytest.mark.integration
@pytest.mark.auth
class TestOAuthAuthorize:
    """Tests for GET /auth/oauth/{provider}/authorize endpoint."""

    @pytest.mark.asyncio
    async def test_oauth_authorize_unsupported_provider(
        self, test_client: AsyncClient
    ) -> None:
        """Test OAuth authorize with unsupported provider returns 400."""
        response = await test_client.get("/auth/oauth/unsupported/authorize")

        assert response.status_code == 400
        assert "unsupported" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_oauth_authorize_unconfigured_provider(
        self, test_client: AsyncClient
    ) -> None:
        """Test OAuth authorize with unconfigured provider returns 503."""
        mock_oauth = MockOAuthRegistry()

        with patch("edcraft_backend.routers.auth.oauth", mock_oauth):
            response = await test_client.get(
                "/auth/oauth/github/authorize", follow_redirects=False
            )

            assert response.status_code == 503
            assert "not configured" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_oauth_authorize_github_success(
        self, test_client: AsyncClient
    ) -> None:
        """Test OAuth authorize with GitHub provider initiates redirect."""
        # Mock OAuth registry with registered GitHub client
        mock_oauth = MockOAuthRegistry()
        mock_oauth.register("github")

        with patch("edcraft_backend.routers.auth.oauth", mock_oauth):
            response = await test_client.get(
                "/auth/oauth/github/authorize", follow_redirects=False
            )

            assert response.status_code in [302, 303]
            assert "github.com" in response.headers["location"]


@pytest.mark.integration
@pytest.mark.auth
class TestOAuthCallback:
    """Tests for GET /auth/oauth/{provider}/callback endpoint."""

    @pytest.mark.asyncio
    async def test_oauth_callback_unsupported_provider(
        self, test_client: AsyncClient
    ) -> None:
        """Test OAuth callback with unsupported provider redirects with error."""
        response = await test_client.get(
            "/auth/oauth/unsupported/callback", follow_redirects=False
        )

        assert response.status_code in [302, 303, 307]

        # Parse redirect URL
        location = response.headers["location"]
        parsed = urlparse(location)
        params = parse_qs(parsed.query)

        assert "/auth/callback" in location
        assert params["success"][0] == "false"
        assert "Unsupported" in params["error"][0]

    @pytest.mark.asyncio
    async def test_oauth_callback_unconfigured_provider(
        self, test_client: AsyncClient
    ) -> None:
        """Test OAuth callback with unconfigured provider redirects with error."""
        mock_oauth = MockOAuthRegistry()

        with patch("edcraft_backend.routers.auth.oauth", mock_oauth):
            response = await test_client.get(
                "/auth/oauth/github/callback",
                params={"code": "test_code"},
                follow_redirects=False,
            )

            assert response.status_code in [302, 303, 307]

            # Parse redirect URL
            location = response.headers["location"]
            parsed = urlparse(location)
            params = parse_qs(parsed.query)

            assert "/auth/callback" in location
            assert params["success"][0] == "false"
            assert "not configured" in params["error"][0]

    @pytest.mark.asyncio
    async def test_oauth_callback_success_creates_new_user(
        self, test_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test OAuth callback creates new user and redirects with success."""
        # Mock OAuth registry and client
        mock_oauth = MockOAuthRegistry()
        mock_oauth.register("github")

        # Mock user info returned by GitHub
        mock_user_info = OAuthUserInfo(
            provider_user_id="12345",
            email="github_user@example.com",
            name="github_user",
        )

        with patch("edcraft_backend.routers.auth.oauth", mock_oauth):
            with patch(
                "edcraft_backend.routers.auth.PROVIDER_HANDLERS",
                {"github": AsyncMock(return_value=mock_user_info)},
            ):
                response = await test_client.get(
                    "/auth/oauth/github/callback",
                    params={"code": "test_code"},
                    follow_redirects=False,
                )

                # Verify redirect with success
                assert response.status_code in [302, 303, 307]

                # Parse redirect URL
                location = response.headers["location"]
                parsed = urlparse(location)
                params = parse_qs(parsed.query)

                assert "/auth/callback" in location
                assert params["success"][0] == "true"

                # Verify cookies are set
                assert "access_token" in response.cookies
                assert "refresh_token" in response.cookies

                # Verify user was created in database
                from sqlalchemy import select

                from edcraft_backend.models.user import User

                result = await db_session.execute(
                    select(User).where(User.email == "github_user@example.com")
                )
                user = result.scalar_one()
                assert user is not None
                assert user.name == "github_user"

                # Verify OAuth account was created
                assert len(user.oauth_accounts) == 1
                assert user.oauth_accounts[0].provider == "github"
                assert user.oauth_accounts[0].provider_user_id == "12345"

    @pytest.mark.asyncio
    async def test_oauth_callback_links_existing_user(
        self, test_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test OAuth callback links OAuth account to existing user."""
        # Create existing user
        existing_user = await create_test_user(
            db_session, email="existing_oauth@example.com", name="existing_user"
        )
        await db_session.commit()

        # Mock OAuth
        mock_oauth = MockOAuthRegistry()
        mock_oauth.register("github")

        mock_user_info = OAuthUserInfo(
            provider_user_id="67890",
            email="existing_oauth@example.com",
            name="existing_user",
        )

        with patch("edcraft_backend.routers.auth.oauth", mock_oauth):
            with patch(
                "edcraft_backend.routers.auth.PROVIDER_HANDLERS",
                {"github": AsyncMock(return_value=mock_user_info)},
            ):
                response = await test_client.get(
                    "/auth/oauth/github/callback",
                    params={"code": "test_code"},
                    follow_redirects=False,
                )

                # Verify redirect with success
                assert response.status_code in [302, 303, 307]

                # Parse redirect URL
                location = response.headers["location"]
                parsed = urlparse(location)
                params = parse_qs(parsed.query)

                assert "/auth/callback" in location
                assert params["success"][0] == "true"

                # Verify OAuth account is linked to existing user
                await db_session.refresh(existing_user)
                assert len(existing_user.oauth_accounts) == 1
                assert existing_user.oauth_accounts[0].provider == "github"
                assert existing_user.oauth_accounts[0].provider_user_id == "67890"

    @pytest.mark.asyncio
    async def test_oauth_callback_existing_oauth_account_login(
        self, test_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test OAuth callback logs in user with existing OAuth account."""
        # Create user with OAuth account
        user = await create_test_user(
            db_session, email="oauth_user@example.com", name="oauth_user"
        )
        await db_session.commit()

        # Create OAuth account manually
        from edcraft_backend.models.oauth_account import OAuthAccount

        oauth_account = OAuthAccount(
            user_id=user.id, provider="github", provider_user_id="99999"
        )
        db_session.add(oauth_account)
        await db_session.commit()

        # Mock OAuth
        mock_oauth = MockOAuthRegistry()
        mock_oauth.register("github")

        mock_user_info = OAuthUserInfo(
            provider_user_id="99999",
            email="oauth_user@example.com",
            name="oauth_user",
        )

        with patch("edcraft_backend.routers.auth.oauth", mock_oauth):
            with patch(
                "edcraft_backend.routers.auth.PROVIDER_HANDLERS",
                {"github": AsyncMock(return_value=mock_user_info)},
            ):
                response = await test_client.get(
                    "/auth/oauth/github/callback",
                    params={"code": "test_code"},
                    follow_redirects=False,
                )

                # Verify redirect with success
                assert response.status_code in [302, 303, 307]

                # Parse redirect URL
                location = response.headers["location"]
                parsed = urlparse(location)
                params = parse_qs(parsed.query)

                assert "/auth/callback" in location
                assert params["success"][0] == "true"

                # Verify cookies are set
                assert "access_token" in response.cookies
                assert "refresh_token" in response.cookies

                # Verify it's the same user (not a new one created)
                from sqlalchemy import select

                from edcraft_backend.models.user import User

                result = await db_session.execute(select(User))
                all_users = result.scalars().all()
                assert len(all_users) == 1
                assert all_users[0].id == user.id


@pytest.mark.integration
@pytest.mark.auth
class TestVerifyEmail:
    """Tests for POST /auth/verify-email endpoint."""

    @pytest.mark.asyncio
    async def test_verify_email_success(
        self, test_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test successful email verification activates user."""
        from datetime import UTC, datetime, timedelta

        from sqlalchemy import select

        from edcraft_backend.models.one_time_token import OneTimeToken, TokenType
        from edcraft_backend.models.user import User
        from edcraft_backend.security import generate_token, hash_token

        # Create inactive user
        user = User(
            email="verify@example.com",
            name="verify",
            password_hash="hashed",
            is_active=False,
        )
        db_session.add(user)
        await db_session.flush()

        # Create verification token
        raw_token = generate_token(32)
        token_hash = hash_token(raw_token)
        expires_at = datetime.now(UTC) + timedelta(hours=24)

        verification_token = OneTimeToken(
            user_id=user.id,
            token_hash=token_hash,
            token_type=TokenType.EMAIL_VERIFICATION,
            expires_at=expires_at,
        )
        db_session.add(verification_token)
        await db_session.commit()

        # Verify email
        response = await test_client.post(
            "/auth/verify-email", json={"token": raw_token}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Email verified successfully"
        assert data["email"] == "verify@example.com"

        # Check user is now active
        result = await db_session.execute(select(User).where(User.id == user.id))
        updated_user = result.scalar_one()
        assert updated_user.is_active is True

        # Check token is marked as used
        await db_session.refresh(verification_token)
        assert verification_token.is_used is True

    @pytest.mark.asyncio
    async def test_verify_email_already_active(
        self, test_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test verifying an already active user returns success."""
        from datetime import UTC, datetime, timedelta

        from edcraft_backend.models.one_time_token import OneTimeToken, TokenType
        from edcraft_backend.security import generate_token, hash_token

        # Create active user
        user = await create_test_user(
            db_session,
            email="active@example.com",
            password_hash="hashed",
            is_active=True,
        )
        await db_session.commit()

        # Create verification token
        raw_token = generate_token(32)
        token_hash = hash_token(raw_token)
        expires_at = datetime.now(UTC) + timedelta(hours=24)

        verification_token = OneTimeToken(
            user_id=user.id,
            token_hash=token_hash,
            token_type=TokenType.EMAIL_VERIFICATION,
            expires_at=expires_at,
        )
        db_session.add(verification_token)
        await db_session.commit()

        # Verify email
        response = await test_client.post(
            "/auth/verify-email", json={"token": raw_token}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "active@example.com"

    @pytest.mark.asyncio
    async def test_verify_email_invalid_token(self, test_client: AsyncClient) -> None:
        """Test email verification with invalid token returns 401."""
        response = await test_client.post(
            "/auth/verify-email", json={"token": "invalid_token_12345678901234567890"}
        )

        assert response.status_code == 401
        assert "invalid" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_verify_email_expired_token(
        self, test_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test email verification with expired token returns 401."""
        from datetime import UTC, datetime, timedelta

        from edcraft_backend.models.one_time_token import OneTimeToken, TokenType
        from edcraft_backend.models.user import User
        from edcraft_backend.security import generate_token, hash_token

        # Create inactive user
        user = User(
            email="expired@example.com",
            name="expired",
            password_hash="hashed",
            is_active=False,
        )
        db_session.add(user)
        await db_session.flush()

        # Create expired token
        raw_token = generate_token(32)
        token_hash = hash_token(raw_token)
        expires_at = datetime.now(UTC) - timedelta(hours=1)  # Expired

        expired_token = OneTimeToken(
            user_id=user.id,
            token_hash=token_hash,
            token_type=TokenType.EMAIL_VERIFICATION,
            expires_at=expires_at,
        )
        db_session.add(expired_token)
        await db_session.commit()

        # Try to verify with expired token
        response = await test_client.post(
            "/auth/verify-email", json={"token": raw_token}
        )

        assert response.status_code == 401
        assert (
            "invalid" in response.json()["detail"].lower()
            or "expired" in response.json()["detail"].lower()
        )

    @pytest.mark.asyncio
    async def test_verify_email_used_token(
        self, test_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test email verification with already used token returns 401."""
        from datetime import UTC, datetime, timedelta

        from edcraft_backend.models.one_time_token import OneTimeToken, TokenType
        from edcraft_backend.models.user import User
        from edcraft_backend.security import generate_token, hash_token

        # Create inactive user
        user = User(
            email="used@example.com",
            name="used",
            password_hash="hashed",
            is_active=False,
        )
        db_session.add(user)
        await db_session.flush()

        # Create used token
        raw_token = generate_token(32)
        token_hash = hash_token(raw_token)
        expires_at = datetime.now(UTC) + timedelta(hours=24)

        used_token = OneTimeToken(
            user_id=user.id,
            token_hash=token_hash,
            token_type=TokenType.EMAIL_VERIFICATION,
            expires_at=expires_at,
            is_used=True,  # Already used
        )
        db_session.add(used_token)
        await db_session.commit()

        # Try to verify with used token
        response = await test_client.post(
            "/auth/verify-email", json={"token": raw_token}
        )

        assert response.status_code == 401
        assert "invalid" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_verify_email_wrong_token_type(
        self, test_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test email verification with password reset token returns 401."""
        from datetime import UTC, datetime, timedelta

        from edcraft_backend.models.one_time_token import OneTimeToken, TokenType
        from edcraft_backend.models.user import User
        from edcraft_backend.security import generate_token, hash_token

        # Create inactive user
        user = User(
            email="wrongtype@example.com",
            name="wrongtype",
            password_hash="hashed",
            is_active=False,
        )
        db_session.add(user)
        await db_session.flush()

        # Create password reset token (wrong type)
        raw_token = generate_token(32)
        token_hash = hash_token(raw_token)
        expires_at = datetime.now(UTC) + timedelta(hours=24)

        wrong_type_token = OneTimeToken(
            user_id=user.id,
            token_hash=token_hash,
            token_type=TokenType.PASSWORD_RESET,  # Wrong type
            expires_at=expires_at,
        )
        db_session.add(wrong_type_token)
        await db_session.commit()

        # Try to verify with wrong token type
        response = await test_client.post(
            "/auth/verify-email", json={"token": raw_token}
        )

        assert response.status_code == 401
        assert "invalid" in response.json()["detail"].lower()


@pytest.mark.integration
@pytest.mark.auth
class TestResendVerification:
    """Tests for POST /auth/resend-verification endpoint."""

    @pytest.mark.asyncio
    async def test_resend_verification_success(
        self, test_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test resending verification email for unverified user."""
        from unittest.mock import AsyncMock, patch

        from edcraft_backend.models.user import User

        # Create inactive user
        user = User(
            email="resend@example.com",
            name="resend",
            password_hash="hashed",
            is_active=False,
        )
        db_session.add(user)
        await db_session.flush()

        # Mock email service
        with patch(
            "edcraft_backend.services.auth_service.AuthService._send_verification_email",
            new_callable=AsyncMock,
        ):
            response = await test_client.post(
                "/auth/resend-verification", json={"email": "resend@example.com"}
            )

            assert response.status_code == 200
            data = response.json()
            assert "verification email has been sent" in data["message"].lower()

    @pytest.mark.asyncio
    async def test_resend_verification_nonexistent_email(
        self, test_client: AsyncClient
    ) -> None:
        """Test resending verification for non-existent email returns generic success."""
        response = await test_client.post(
            "/auth/resend-verification", json={"email": "nonexistent@example.com"}
        )

        # Should still return 200 to prevent user enumeration
        assert response.status_code == 200
        data = response.json()
        assert "verification email has been sent" in data["message"].lower()

    @pytest.mark.asyncio
    async def test_resend_verification_already_verified(
        self, test_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test resending verification for already verified user returns generic success."""
        # Create active user
        await create_test_user(
            db_session,
            email="verified@example.com",
            password_hash="hashed",
            is_active=True,
        )
        await db_session.commit()

        response = await test_client.post(
            "/auth/resend-verification", json={"email": "verified@example.com"}
        )

        # Should still return 200 to prevent user enumeration
        assert response.status_code == 200
        data = response.json()
        assert "verification email has been sent" in data["message"].lower()

    @pytest.mark.asyncio
    async def test_resend_verification_revokes_old_tokens(
        self, test_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test resending verification revokes old tokens before creating new one."""
        from datetime import UTC, datetime, timedelta
        from unittest.mock import AsyncMock, patch

        from edcraft_backend.models.one_time_token import OneTimeToken, TokenType
        from edcraft_backend.models.user import User
        from edcraft_backend.security import generate_token, hash_token

        # Create inactive user
        user = User(
            email="revoke@example.com",
            name="revoke",
            password_hash="hashed",
            is_active=False,
        )
        db_session.add(user)
        await db_session.flush()

        # Create old verification token
        raw_token = generate_token(32)
        token_hash = hash_token(raw_token)
        expires_at = datetime.now(UTC) + timedelta(hours=24)

        old_token = OneTimeToken(
            user_id=user.id,
            token_hash=token_hash,
            token_type=TokenType.EMAIL_VERIFICATION,
            expires_at=expires_at,
        )
        db_session.add(old_token)
        await db_session.commit()

        # Mock email service
        with patch(
            "edcraft_backend.services.auth_service.AuthService._send_verification_email",
            new_callable=AsyncMock,
        ):
            response = await test_client.post(
                "/auth/resend-verification", json={"email": "revoke@example.com"}
            )

            assert response.status_code == 200

            # Check old token is marked as used
            await db_session.refresh(old_token)
            assert old_token.is_used is True
