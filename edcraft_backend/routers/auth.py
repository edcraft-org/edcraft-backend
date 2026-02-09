"""Authentication endpoints."""

from urllib.parse import quote

from authlib.integrations.base_client import OAuthError
from fastapi import APIRouter, Cookie, HTTPException, Request, Response, status
from starlette.responses import RedirectResponse

from edcraft_backend.config import settings
from edcraft_backend.dependencies import AuthServiceDep, CurrentUserDep, OAuthServiceDep
from edcraft_backend.exceptions import EdCraftBaseException
from edcraft_backend.models.user import User
from edcraft_backend.oauth.config import SUPPORTED_PROVIDERS, OAuthProvider
from edcraft_backend.oauth.providers import PROVIDER_HANDLERS
from edcraft_backend.oauth.registry import oauth
from edcraft_backend.schemas.auth import (
    AuthUserResponse,
    LoginRequest,
    ResendVerificationRequest,
    ResendVerificationResponse,
    SignupRequest,
    TokenPairResponse,
    VerifyEmailRequest,
    VerifyEmailResponse,
)

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post(
    "/signup", response_model=AuthUserResponse, status_code=status.HTTP_201_CREATED
)
async def signup(data: SignupRequest, service: AuthServiceDep) -> User:
    """Sign up a new user account."""
    try:
        return await service.signup(data.email, data.password)
    except EdCraftBaseException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e


@router.post("/login")
async def login(
    data: LoginRequest, request: Request, response: Response, service: AuthServiceDep
) -> TokenPairResponse:
    """Login with email and password. Tokens are set as httpOnly cookies."""
    try:
        tokens = await service.login(
            data.email,
            data.password,
            ip_address=_get_client_ip(request),
            user_agent=_get_user_agent(request),
        )
    except EdCraftBaseException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e

    _set_token_cookies(response, tokens)
    return tokens


@router.post("/refresh")
async def refresh_token(
    request: Request,
    response: Response,
    service: AuthServiceDep,
    refresh_token: str | None = Cookie(None),
) -> TokenPairResponse:
    """Rotate tokens using the refresh token cookie."""
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token missing"
        )
    try:
        tokens = await service.refresh_access_token(
            refresh_token,
            ip_address=_get_client_ip(request),
            user_agent=_get_user_agent(request),
        )
    except EdCraftBaseException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e

    _set_token_cookies(response, tokens)
    return tokens


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    current_user: CurrentUserDep,
    response: Response,
    service: AuthServiceDep,
    refresh_token: str | None = Cookie(None),
) -> None:
    """Revoke refresh token and clear cookies."""
    if refresh_token:
        try:
            await service.logout(refresh_token)
        except EdCraftBaseException as e:
            raise HTTPException(status_code=e.status_code, detail=e.message) from e
    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token")


@router.get("/me", response_model=AuthUserResponse)
async def get_me(current_user: CurrentUserDep) -> User:
    """Return the authenticated user's profile."""
    return current_user


@router.post("/verify-email", status_code=status.HTTP_200_OK)
async def verify_email(
    data: VerifyEmailRequest,
    service: AuthServiceDep,
) -> VerifyEmailResponse:
    """Verify email address with token."""
    try:
        user = await service.verify_email(data.token)
        return VerifyEmailResponse(
            message="Email verified successfully",
            email=user.email,
        )
    except EdCraftBaseException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e


@router.post("/resend-verification", status_code=status.HTTP_200_OK)
async def resend_verification(
    data: ResendVerificationRequest,
    service: AuthServiceDep,
) -> ResendVerificationResponse:
    """Resend verification email."""
    try:
        await service.resend_verification_email(data.email)
        return ResendVerificationResponse(
            message="If the email exists and is unverified, a verification email has been sent"
        )
    except EdCraftBaseException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e


@router.get("/oauth/{provider}/authorize")
async def oauth_authorize(
    provider: str, request: Request, state: str | None = None
) -> RedirectResponse:
    """Redirect to the OAuth provider's authorization page."""
    if provider not in SUPPORTED_PROVIDERS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported OAuth provider: {provider}",
        )

    client = oauth.create_client(provider)
    if not client:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"OAuth provider {provider} is not configured",
        )

    redirect_uri = settings.oauth_github.redirect_uri
    redirect: RedirectResponse = await client.authorize_redirect(
        request, redirect_uri, state=state
    )
    return redirect


@router.get("/oauth/{provider}/callback")
async def oauth_callback(
    provider: str,
    request: Request,
    response: Response,
    oauth_svc: OAuthServiceDep,
    state: str | None = None,
) -> RedirectResponse:
    """Handle provider callback and issue tokens."""
    if provider not in SUPPORTED_PROVIDERS:
        return _redirect_to_frontend_error(
            f"Unsupported OAuth provider: {provider}", state
        )

    client = oauth.create_client(provider)
    if not client:
        return _redirect_to_frontend_error(
            f"OAuth provider {provider} is not configured", state
        )

    try:
        token = await client.authorize_access_token(request)

        provider_enum = OAuthProvider(provider)
        handler = PROVIDER_HANDLERS[provider_enum]
        user_info = await handler(client, token)

        tokens = await oauth_svc.handle_oauth_callback(
            provider=provider,
            provider_user_id=user_info.provider_user_id,
            email=user_info.email,
            name=user_info.name,
            ip_address=_get_client_ip(request),
            user_agent=_get_user_agent(request),
        )

        redirect_response = _redirect_to_frontend_success(state)
        _set_token_cookies(redirect_response, tokens)

        return redirect_response

    except OAuthError as e:
        return _redirect_to_frontend_error(f"OAuth provider error: {str(e)}", state)
    except EdCraftBaseException as e:
        return _redirect_to_frontend_error(e.message, state)


def _get_client_ip(request: Request) -> str | None:
    """Extract client IP address, respecting X-Forwarded-For if present."""
    if forwarded := request.headers.get("x-forwarded-for"):
        # X-Forwarded-For can contain multiple IPs; take the first one
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return None


def _get_user_agent(request: Request) -> str | None:
    """Extract user agent from request headers."""
    return request.headers.get("user-agent")


def _set_token_cookies(response: Response, tokens: TokenPairResponse) -> None:
    """Attach access_token and refresh_token as httpOnly cookies."""
    secure = settings.is_production
    response.set_cookie(
        key="access_token",
        value=tokens.access_token,
        httponly=True,
        secure=secure,
        samesite="lax",
        max_age=settings.jwt.access_token_expire_minutes * 60,
    )
    response.set_cookie(
        key="refresh_token",
        value=tokens.refresh_token,
        httponly=True,
        secure=secure,
        samesite="lax",
        max_age=settings.jwt.refresh_token_expire_days * 24 * 60 * 60,
    )


def _redirect_to_frontend_success(state: str | None) -> RedirectResponse:
    """Redirect to frontend with success status."""
    params = "success=true"
    if state:
        params += f"&state={quote(state)}"
    return RedirectResponse(url=f"{settings.frontend_url}/auth/callback?{params}")


def _redirect_to_frontend_error(error: str, state: str | None) -> RedirectResponse:
    """Redirect to frontend with error status."""
    params = f"success=false&error={quote(error)}"
    if state:
        params += f"&state={quote(state)}"
    return RedirectResponse(url=f"{settings.frontend_url}/auth/callback?{params}")
