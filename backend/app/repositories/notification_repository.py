import uuid
from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import ColumnElement, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification
from app.repositories.query_helpers import fetch_page
from app.schemas.pagination import PageParams


class NotificationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def add(self, notification: Notification) -> None:
        self._session.add(notification)

    async def get_for_user(
        self,
        user_id: uuid.UUID,
        notification_id: uuid.UUID,
    ) -> Notification | None:
        result = await self._session.execute(
            select(Notification).where(
                Notification.id == notification_id,
                Notification.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_for_user(
        self,
        user_id: uuid.UUID,
        *,
        unread_only: bool,
        page: PageParams,
    ) -> tuple[Sequence[Notification], int]:
        conditions: list[ColumnElement[bool]] = [Notification.user_id == user_id]
        if unread_only:
            conditions.append(Notification.read_at.is_(None))
        return await fetch_page(
            self._session,
            select(Notification),
            conditions,
            [Notification.created_at.desc(), Notification.id.desc()],
            page,
        )

    async def count_unread(self, user_id: uuid.UUID) -> int:
        count = await self._session.scalar(
            select(func.count())
            .select_from(Notification)
            .where(Notification.user_id == user_id, Notification.read_at.is_(None))
        )
        return count or 0

    async def mark_all_read(self, user_id: uuid.UUID, read_at: datetime) -> None:
        await self._session.execute(
            update(Notification)
            .where(Notification.user_id == user_id, Notification.read_at.is_(None))
            .values(read_at=read_at)
        )
