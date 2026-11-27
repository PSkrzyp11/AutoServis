import uuid
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.errors import ConflictError, ErrorCode, ForbiddenError, UnauthorizedError
from app.core.logging import get_logger
from app.core.security import (
    AccessToken,
    create_access_token,
    decode_access_token,
    dummy_password_hash,
    generate_opaque_token,
    hash_opaque_token,
    hash_password,
    password_needs_rehash,
    verify_password,
)
from app.core.time import utc_now
from app.models.enums import UserRole
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.repositories.user_repository import UserRepository
from app.schemas.auth import RegisterRequest

logger = get_logger()


@dataclass(frozen=True)
class IssuedTokens:
    access_token: AccessToken
    refresh_token: str
    refresh_token_expires_at: datetime


class AuthService:
    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        self._session = session
        self._settings = settings
        self._users = UserRepository(session)
        self._refresh_tokens = RefreshTokenRepository(session)

    async def register(self, data: RegisterRequest) -> User:
        if await self._users.get_by_email(data.email) is not None:
            raise self._email_taken_error()

        user = User(
            email=data.email,
            password_hash=hash_password(data.password),
            full_name=data.full_name,
            phone=data.phone,
            role=UserRole.CLIENT,
            is_active=True,
        )
        self._users.add(user)
        try:
            await self._session.commit()
        except IntegrityError as error:
            await self._session.rollback()
            raise self._email_taken_error() from error

        logger.info("user_registered", user_id=str(user.id))
        return user

    async def login(self, *, email: str, password: str) -> IssuedTokens:
        user = await self._authenticate(email=email, password=password)
        tokens = self._issue_tokens(user.id, family_id=uuid.uuid4(), now=utc_now())
        await self._session.commit()
        logger.info("user_logged_in", user_id=str(user.id))
        return tokens

    async def refresh(self, raw_refresh_token: str) -> IssuedTokens:
        now = utc_now()
        token = await self._refresh_tokens.get_by_hash_for_update(
            hash_opaque_token(raw_refresh_token)
        )
        if token is None:
            raise UnauthorizedError(ErrorCode.INVALID_TOKEN, "Refresh token is invalid")

        if token.revoked_at is not None:
            await self._refresh_tokens.revoke_family(token.family_id, now)
            await self._session.commit()
            logger.warning("refresh_token_reuse_detected", user_id=str(token.user_id))
            raise UnauthorizedError(ErrorCode.INVALID_TOKEN, "Refresh token is invalid")

        if token.expires_at <= now:
            raise UnauthorizedError(ErrorCode.TOKEN_EXPIRED, "Refresh token has expired")

        user = await self._users.get_by_id(token.user_id)
        if user is None or not user.is_active:
            await self._refresh_tokens.revoke_family(token.family_id, now)
            await self._session.commit()
            raise ForbiddenError(ErrorCode.USER_INACTIVE, "User account is inactive")

        token.revoked_at = now
        tokens = self._issue_tokens(user.id, family_id=token.family_id, now=now)
        await self._session.commit()
        return tokens

    async def logout(self, raw_refresh_token: str | None) -> None:
        if raw_refresh_token is None:
            return
        token = await self._refresh_tokens.get_by_hash_for_update(
            hash_opaque_token(raw_refresh_token)
        )
        if token is None:
            return
        await self._refresh_tokens.revoke_family(token.family_id, utc_now())
        await self._session.commit()
        logger.info("user_logged_out", user_id=str(token.user_id))

    async def get_user_from_access_token(self, access_token: str) -> User:
        user_id = decode_access_token(access_token, self._settings)
        user = await self._users.get_by_id(user_id)
        if user is None:
            raise UnauthorizedError(ErrorCode.INVALID_TOKEN, "Access token is invalid")
        if not user.is_active:
            raise ForbiddenError(ErrorCode.USER_INACTIVE, "User account is inactive")
        return user

    async def _authenticate(self, *, email: str, password: str) -> User:
        user = await self._users.get_by_email(email)
        if user is None or user.password_hash is None:
            verify_password(password, dummy_password_hash())
            raise self._invalid_credentials_error()

        if not verify_password(password, user.password_hash):
            raise self._invalid_credentials_error()

        if not user.is_active:
            raise ForbiddenError(ErrorCode.USER_INACTIVE, "User account is inactive")

        if password_needs_rehash(user.password_hash):
            user.password_hash = hash_password(password)
        return user

    def _issue_tokens(
        self,
        user_id: uuid.UUID,
        *,
        family_id: uuid.UUID,
        now: datetime,
    ) -> IssuedTokens:
        raw_refresh_token = generate_opaque_token()
        refresh_token_expires_at = now + self._settings.refresh_token_ttl
        self._refresh_tokens.add(
            RefreshToken(
                user_id=user_id,
                token_hash=hash_opaque_token(raw_refresh_token),
                family_id=family_id,
                expires_at=refresh_token_expires_at,
            )
        )
        return IssuedTokens(
            access_token=create_access_token(user_id, self._settings, now),
            refresh_token=raw_refresh_token,
            refresh_token_expires_at=refresh_token_expires_at,
        )

    @staticmethod
    def _invalid_credentials_error() -> UnauthorizedError:
        return UnauthorizedError(ErrorCode.INVALID_CREDENTIALS, "Invalid email or password")

    @staticmethod
    def _email_taken_error() -> ConflictError:
        return ConflictError(
            ErrorCode.EMAIL_ALREADY_REGISTERED,
            "An account with this email address already exists",
        )
