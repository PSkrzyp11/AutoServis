import uuid
from collections.abc import Sequence
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ConflictError, ErrorCode, NotFoundError
from app.core.logging import get_logger
from app.models.workshop import Workshop, WorkshopClosure, WorkshopOpeningHours
from app.repositories.workshop_schedule_repository import WorkshopScheduleRepository
from app.schemas.workshop import ClosureCreate, OpeningHoursUpdate
from app.services.workshop_service import local_today

logger = get_logger()


class WorkshopScheduleService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._schedule = WorkshopScheduleRepository(session)

    async def list_opening_hours(self, workshop: Workshop) -> Sequence[WorkshopOpeningHours]:
        return await self._schedule.list_opening_hours(workshop.id)

    async def replace_opening_hours(
        self,
        workshop: Workshop,
        data: OpeningHoursUpdate,
    ) -> Sequence[WorkshopOpeningHours]:
        await self._schedule.replace_opening_hours(
            workshop.id,
            [
                WorkshopOpeningHours(
                    workshop_id=workshop.id,
                    weekday=day.weekday,
                    opens_at=day.opens_at,
                    closes_at=day.closes_at,
                )
                for day in data.days
            ],
        )
        await self._session.commit()
        logger.info("opening_hours_replaced", workshop_id=str(workshop.id), days=len(data.days))
        return await self._schedule.list_opening_hours(workshop.id)

    async def list_closures(
        self,
        workshop: Workshop,
        from_date: date | None,
    ) -> Sequence[WorkshopClosure]:
        return await self._schedule.list_closures(
            workshop.id,
            from_date=from_date or local_today(workshop),
        )

    async def add_closure(self, workshop: Workshop, data: ClosureCreate) -> WorkshopClosure:
        if await self._schedule.closure_exists(workshop.id, data.closed_on):
            raise ConflictError(
                ErrorCode.CLOSURE_ALREADY_EXISTS,
                "The workshop is already closed on this date",
            )
        closure = WorkshopClosure(
            workshop_id=workshop.id,
            closed_on=data.closed_on,
            reason=data.reason,
        )
        self._schedule.add_closure(closure)
        await self._session.commit()
        logger.info("closure_added", workshop_id=str(workshop.id), closed_on=str(data.closed_on))
        return closure

    async def delete_closure(self, workshop: Workshop, closure_id: uuid.UUID) -> None:
        if not await self._schedule.delete_closure(workshop.id, closure_id):
            raise NotFoundError("Closure not found")
        await self._session.commit()
