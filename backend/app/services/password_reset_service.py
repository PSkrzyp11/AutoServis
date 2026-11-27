from urllib.parse import urlencode

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.errors import AppError, ErrorCode
from app.core.logging import get_logger
from app.core.security import generate_opaque_token, hash_opaque_token, hash_password
from app.core.time import utc_now
from app.models.password_reset_token import PasswordResetToken
from app.repositories.password_reset_token_repository import PasswordResetTokenRepository
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.repositories.user_repository import UserRepository
from app.workers.queue import TaskQueue

logger = get_logger()


class PasswordResetService:
    def __init__(self, session: AsyncSession, settings: Settings, task_queue: TaskQueue) -> None:
        self._session = session
        self._settings = settings
        self._task_queue = task_queue
        self._users = UserRepository(session)
        self._reset_tokens = PasswordResetTokenRepository(session)
        self._refresh_tokens = RefreshTokenRepository(session)

    async def request_reset(self, email: str) -> None:
        user = await self._users.get_by_email(email)
        if user is None or not user.is_active:
            logger.info("password_reset_requested_for_unknown_account")
            return

        now = utc_now()
        await self._reset_tokens.invalidate_unused_for_user(user.id, now)
        raw_token = generate_opaque_token()
        self._reset_tokens.add(
            PasswordResetToken(
                user_id=user.id,
                token_hash=hash_opaque_token(raw_token),
                expires_at=now + self._settings.password_reset_token_ttl,
            )
        )
        await self._session.commit()

        await self._task_queue.enqueue_password_reset_email(
            recipient=user.email,
            full_name=user.full_name,
            reset_url=self._build_reset_url(raw_token),
        )
        logger.info("password_reset_requested", user_id=str(user.id))

    async def confirm_reset(self, *, raw_token: str, new_password: str) -> None:
        now = utc_now()
        token = await self._reset_tokens.get_by_hash_for_update(hash_opaque_token(raw_token))
        if token is None or token.used_at is not None or token.expires_at <= now:
            raise self._invalid_token_error()

        user = await self._users.get_by_id(token.user_id)
        if user is None or not user.is_active:
            raise self._invalid_token_error()

        user.password_hash = hash_password(new_password)
        token.used_at = now
        await self._refresh_tokens.revoke_all_for_user(user.id, now)
        await self._session.commit()
        logger.info("password_reset_completed", user_id=str(user.id))

    def _build_reset_url(self, raw_token: str) -> str:
        return f"{self._settings.frontend_password_reset_url}?{urlencode({'token': raw_token})}"

    @staticmethod
    def _invalid_token_error() -> AppError:
        return AppError(ErrorCode.INVALID_TOKEN, "Password reset token is invalid or expired")
