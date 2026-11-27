from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, Response, status
from fastapi.responses import JSONResponse

from app.api.cookies import REFRESH_TOKEN_COOKIE, clear_session_cookies, set_session_cookies
from app.api.dependencies import (
    LOGIN_RATE_LIMIT,
    PASSWORD_RESET_RATE_LIMIT,
    REGISTER_RATE_LIMIT,
    AuthServiceDep,
    PasswordResetServiceDep,
    rate_limited,
)
from app.core.config import Settings
from app.core.dependencies import SettingsDep
from app.core.errors import AppError, ErrorCode, UnauthorizedError
from app.core.exception_handlers import error_response_from
from app.schemas.auth import (
    AccessTokenResponse,
    LoginRequest,
    PasswordResetConfirmRequest,
    PasswordResetRequest,
    RegisterRequest,
)
from app.schemas.errors import error_responses
from app.schemas.user import UserRead
from app.services.auth_service import IssuedTokens

router = APIRouter(prefix="/auth", tags=["auth"])

RefreshTokenCookie = Annotated[
    str | None,
    Cookie(alias=REFRESH_TOKEN_COOKIE, description="HttpOnly refresh token cookie"),
]


def build_token_response(
    tokens: IssuedTokens,
    response: Response,
    settings: Settings,
) -> AccessTokenResponse:
    set_session_cookies(
        response,
        refresh_token=tokens.refresh_token,
        expires_at=tokens.refresh_token_expires_at,
        settings=settings,
    )
    return AccessTokenResponse(
        access_token=tokens.access_token.value,
        expires_in=tokens.access_token.expires_in_seconds,
    )


@router.post(
    "/register",
    status_code=status.HTTP_201_CREATED,
    summary="Register a client account",
    description="Creates a new account with the CLIENT role. Sign in afterwards to get tokens.",
    responses=error_responses(status.HTTP_409_CONFLICT, status.HTTP_429_TOO_MANY_REQUESTS),
    dependencies=[Depends(rate_limited(REGISTER_RATE_LIMIT))],
)
async def register(payload: RegisterRequest, auth_service: AuthServiceDep) -> UserRead:
    user = await auth_service.register(payload)
    return UserRead.model_validate(user)


@router.post(
    "/login",
    summary="Sign in with email and password",
    description=(
        "Returns a short-lived access token and sets the refresh token as an HttpOnly cookie."
    ),
    responses=error_responses(
        status.HTTP_401_UNAUTHORIZED,
        status.HTTP_403_FORBIDDEN,
        status.HTTP_429_TOO_MANY_REQUESTS,
    ),
    dependencies=[Depends(rate_limited(LOGIN_RATE_LIMIT))],
)
async def login(
    payload: LoginRequest,
    response: Response,
    auth_service: AuthServiceDep,
    settings: SettingsDep,
) -> AccessTokenResponse:
    tokens = await auth_service.login(email=payload.email, password=payload.password)
    return build_token_response(tokens, response, settings)


@router.post(
    "/refresh",
    response_model=AccessTokenResponse,
    summary="Rotate the refresh token",
    description=(
        "Exchanges the refresh token cookie for a new access token and a new refresh token. "
        "Reusing an already rotated refresh token revokes the whole session."
    ),
    responses=error_responses(status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN),
)
async def refresh(
    response: Response,
    auth_service: AuthServiceDep,
    settings: SettingsDep,
    refresh_token: RefreshTokenCookie = None,
) -> AccessTokenResponse | JSONResponse:
    try:
        if refresh_token is None:
            raise UnauthorizedError(ErrorCode.UNAUTHORIZED, "Refresh token cookie is missing")
        tokens = await auth_service.refresh(refresh_token)
    except AppError as error:
        error_response = error_response_from(error)
        clear_session_cookies(error_response, settings)
        return error_response
    return build_token_response(tokens, response, settings)


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Sign out",
    description="Revokes the current session and clears the session cookies.",
    responses=error_responses(),
)
async def logout(
    response: Response,
    auth_service: AuthServiceDep,
    settings: SettingsDep,
    refresh_token: RefreshTokenCookie = None,
) -> None:
    await auth_service.logout(refresh_token)
    clear_session_cookies(response, settings)


@router.post(
    "/password-reset/request",
    status_code=status.HTTP_202_ACCEPTED,
    response_class=Response,
    summary="Request a password reset email",
    description=(
        "Always returns 202 to avoid revealing whether an account exists. "
        "If it does, a reset link is sent by email."
    ),
    responses=error_responses(status.HTTP_429_TOO_MANY_REQUESTS),
    dependencies=[Depends(rate_limited(PASSWORD_RESET_RATE_LIMIT))],
)
async def request_password_reset(
    payload: PasswordResetRequest,
    password_reset_service: PasswordResetServiceDep,
) -> Response:
    await password_reset_service.request_reset(payload.email)
    return Response(status_code=status.HTTP_202_ACCEPTED)


@router.post(
    "/password-reset/confirm",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Set a new password using a reset token",
    description="Sets the new password and signs the user out of all sessions.",
    responses=error_responses(status.HTTP_400_BAD_REQUEST),
)
async def confirm_password_reset(
    payload: PasswordResetConfirmRequest,
    password_reset_service: PasswordResetServiceDep,
) -> None:
    await password_reset_service.confirm_reset(
        raw_token=payload.token,
        new_password=payload.new_password,
    )
