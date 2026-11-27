import uuid
from collections.abc import Sequence
from datetime import date

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.workshop import WorkshopClosure, WorkshopOpeningHours


class WorkshopScheduleRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_opening_hours(self, workshop_id: uuid.UUID) -> Sequence[WorkshopOpeningHours]:
        result = await self._session.execute(
            select(WorkshopOpeningHours)
            .where(WorkshopOpeningHours.workshop_id == workshop_id)
            .order_by(WorkshopOpeningHours.weekday)
        )
        return result.scalars().all()

    async def replace_opening_hours(
        self,
        workshop_id: uuid.UUID,
        opening_hours: Sequence[WorkshopOpeningHours],
    ) -> None:
        await self._session.execute(
            delete(WorkshopOpeningHours).where(WorkshopOpeningHours.workshop_id == workshop_id)
        )
        self._session.add_all(opening_hours)

    async def list_closures(
        self,
        workshop_id: uuid.UUID,
        *,
        from_date: date,
        limit: int | None = None,
    ) -> Sequence[WorkshopClosure]:
        query = (
            select(WorkshopClosure)
            .where(
                WorkshopClosure.workshop_id == workshop_id, WorkshopClosure.closed_on >= from_date
            )
            .order_by(WorkshopClosure.closed_on)
            .limit(limit)
        )
        result = await self._session.execute(query)
        return result.scalars().all()

    async def closure_exists(self, workshop_id: uuid.UUID, closed_on: date) -> bool:
        found = await self._session.scalar(
            select(WorkshopClosure.id).where(
                WorkshopClosure.workshop_id == workshop_id,
                WorkshopClosure.closed_on == closed_on,
            )
        )
        return found is not None

    def add_closure(self, closure: WorkshopClosure) -> None:
        self._session.add(closure)

    async def delete_closure(self, workshop_id: uuid.UUID, closure_id: uuid.UUID) -> bool:
        result = await self._session.execute(
            delete(WorkshopClosure)
            .where(WorkshopClosure.workshop_id == workshop_id, WorkshopClosure.id == closure_id)
            .returning(WorkshopClosure.id)
        )
        return result.scalar_one_or_none() is not None
