import uuid
from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.password_reset_token import PasswordResetToken


class PasswordResetTokenRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def add(self, token: PasswordResetToken) -> None:
        self._session.add(token)

    async def get_by_hash_for_update(self, token_hash: str) -> PasswordResetToken | None:
        result = await self._session.execute(
            select(PasswordResetToken)
            .where(PasswordResetToken.token_hash == token_hash)
            .with_for_update()
        )
        return result.scalar_one_or_none()

    async def invalidate_unused_for_user(self, user_id: uuid.UUID, used_at: datetime) -> None:
        await self._session.execute(
            update(PasswordResetToken)
            .where(PasswordResetToken.user_id == user_id, PasswordResetToken.used_at.is_(None))
            .values(used_at=used_at)
        )
