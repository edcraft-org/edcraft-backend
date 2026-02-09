"""Authentication service: register, login, refresh, logout."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING
from uuid import UUID

from edcraft_backend.config import settings
from edcraft_backend.exceptions import (
    AccountInactiveError,
    AuthenticationError,
    DuplicateResourceError,
    InvalidTokenError,
    ResourceNotFoundError,
    TokenDecodeError,
)
from edcraft_backend.models.one_time_token import TokenType
from edcraft_backend.models.user import User
from edcraft_backend.repositories.one_time_token_repository import (
    OneTimeTokenRepository,
)
from edcraft_backend.repositories.refresh_token_repository import RefreshTokenRepository
from edcraft_backend.repositories.user_repository import UserRepository
from edcraft_backend.schemas.auth import TokenPairResponse
from edcraft_backend.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    generate_token,
    hash_password,
    hash_token,
    verify_password,
)

if TYPE_CHECKING:
    from edcraft_backend.services.email_service import EmailService
    from edcraft_backend.services.folder_service import FolderService


class AuthService:
    """Handles registration, login, token refresh, and logout."""

    def __init__(
        self,
        user_repo: UserRepository,
        refresh_token_repo: RefreshTokenRepository,
        one_time_token_repo: OneTimeTokenRepository,
        folder_svc: FolderService,
        email_svc: EmailService,
    ):
        self.user_repo = user_repo
        self.refresh_token_repo = refresh_token_repo
        self.one_time_token_repo = one_time_token_repo
        self.folder_svc = folder_svc
        self.email_svc = email_svc

    async def signup(self, email: str, password: str) -> User:
        """Create a new user (inactive) and send verification email."""
        if await self.user_repo.email_exists(email):
            raise DuplicateResourceError("User", "email", email)

        name = self._generate_name_from_email(email)

        # If email verification is disabled, create user as active immediately
        is_active = not settings.email.enabled

        user = User(
            email=email,
            name=name,
            password_hash=hash_password(password),
            is_active=is_active,
        )
        user = await self.user_repo.create(user)

        await self.folder_svc.create_root_folder(user.id)

        if settings.email.enabled:
            await self._send_verification_email(user)

        return user

    def _generate_name_from_email(self, email: str) -> str:
        """Generate a name from email address."""
        local_part = email.split("@")[0]
        return local_part.lower()

    async def login(
        self,
        email: str,
        password: str,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> TokenPairResponse:
        """Authenticate with email and password, and issue token pair."""
        user = await self.user_repo.get_by_email(email)

        # Same error for bad email or bad password — no user enumeration
        if (
            not user
            or not user.password_hash
            or not verify_password(password, user.password_hash)
        ):
            raise AuthenticationError()

        if not user.is_active:
            raise AccountInactiveError()

        return await self.issue_tokens(user.id, ip_address, user_agent)

    async def refresh_access_token(
        self,
        refresh_token: str,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> TokenPairResponse:
        """Validate refresh token, revoke it, and issue a new token pair."""
        try:
            payload = decode_token(refresh_token)
        except TokenDecodeError as e:
            raise InvalidTokenError() from e

        if payload.get("type") != "refresh":
            raise InvalidTokenError()

        token_hash = hash_token(refresh_token)
        db_token = await self.refresh_token_repo.get(token_hash)

        if (
            not db_token
            or not db_token.is_valid
            or payload.get("sub") != str(db_token.user_id)
        ):
            raise InvalidTokenError()

        # Revoke old refresh token (rotation)
        await self.refresh_token_repo.revoke(db_token.id)

        return await self.issue_tokens(db_token.user_id, ip_address, user_agent)

    async def logout(self, refresh_token: str) -> None:
        """Revoke a refresh token."""
        token_hash = hash_token(refresh_token)
        db_token = await self.refresh_token_repo.get(token_hash)
        if db_token:
            await self.refresh_token_repo.revoke(db_token.id)

    async def issue_tokens(
        self,
        user_id: UUID,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> TokenPairResponse:
        """Create access and refresh tokens, and persist the refresh token hash."""
        now = datetime.now(UTC)
        access_token = create_access_token(str(user_id), now)
        refresh_token = create_refresh_token(str(user_id), now)

        await self.refresh_token_repo.create(
            user_id=user_id,
            token_hash=hash_token(refresh_token),
            expires_at=now + timedelta(days=settings.jwt.refresh_token_expire_days),
            ip_address=ip_address,
            user_agent=user_agent,
        )

        return TokenPairResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",  # noqa: S106
            expires_in=settings.jwt.access_token_expire_minutes * 60,
        )

    async def _send_verification_email(self, user: User) -> None:
        """Generate token and send verification email."""
        raw_token = generate_token(32)
        token_hash = hash_token(raw_token)

        expires_at = datetime.now(UTC) + timedelta(
            hours=settings.email.verification_token_expire_hours
        )

        await self.one_time_token_repo.create(
            user_id=user.id,
            token_hash=token_hash,
            token_type=TokenType.EMAIL_VERIFICATION,
            expires_at=expires_at,
        )

        await self.email_svc.send_verification_email(
            to_email=user.email,
            name=user.name,
            verification_token=raw_token,
        )

    async def verify_email(self, token: str) -> User:
        """Verify email with token and activate user."""
        token_hash = hash_token(token)

        db_token = await self.one_time_token_repo.get_by_token_hash(
            token_hash, TokenType.EMAIL_VERIFICATION
        )

        if not db_token or not db_token.is_valid:
            raise InvalidTokenError("Invalid or expired verification token")

        user = await self.user_repo.get_by_id(db_token.user_id)
        if not user:
            raise ResourceNotFoundError("User", str(db_token.user_id))

        if user.is_active:
            await self.one_time_token_repo.mark_as_used(db_token.id)
            return user

        user.is_active = True
        await self.user_repo.update(user)

        await self.one_time_token_repo.mark_as_used(db_token.id)

        return user

    async def resend_verification_email(self, email: str) -> None:
        """Resend verification email for unverified user."""
        user = await self.user_repo.get_by_email(email)

        if not user:
            # Don't reveal if email exists
            return

        if user.is_active:
            # Already verified, nothing to do
            return

        await self.one_time_token_repo.revoke_all_user_tokens(
            user.id, TokenType.EMAIL_VERIFICATION
        )

        await self._send_verification_email(user)
