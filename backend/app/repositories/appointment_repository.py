import uuid
from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import ColumnElement, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from sqlalchemy.orm.interfaces import LoaderOption

from app.models.appointment import Appointment
from app.models.enums import ACTIVE_APPOINTMENT_STATUSES, AppointmentStatus
from app.repositories.query_helpers import fetch_page
from app.schemas.pagination import PageParams
from app.services.availability import BusyInterval

DETAIL_OPTIONS: tuple[LoaderOption, ...] = (
    joinedload(Appointment.workshop),
    joinedload(Appointment.bay),
    joinedload(Appointment.service_type),
    joinedload(Appointment.vehicle),
    joinedload(Appointment.client),
    joinedload(Appointment.order),
)


class AppointmentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def add(self, appointment: Appointment) -> None:
        self._session.add(appointment)

    async def get_detailed(self, appointment_id: uuid.UUID) -> Appointment | None:
        result = await self._session.execute(
            select(Appointment)
            .options(*DETAIL_OPTIONS)
            .where(Appointment.id == appointment_id)
            .execution_options(populate_existing=True)
        )
        return result.unique().scalar_one_or_none()

    async def get_for_update(self, appointment_id: uuid.UUID) -> Appointment | None:
        result = await self._session.execute(
            select(Appointment).where(Appointment.id == appointment_id).with_for_update()
        )
        return result.scalar_one_or_none()

    async def list_busy_intervals(
        self,
        bay_ids: Sequence[uuid.UUID],
        start_at: datetime,
        end_at: datetime,
    ) -> list[BusyInterval]:
        if not bay_ids:
            return []
        result = await self._session.execute(
            select(Appointment.bay_id, Appointment.start_at, Appointment.end_at).where(
                Appointment.bay_id.in_(bay_ids),
                Appointment.status.in_(ACTIVE_APPOINTMENT_STATUSES),
                Appointment.start_at < end_at,
                Appointment.end_at > start_at,
            )
        )
        return [
            BusyInterval(bay_id=bay_id, start_at=busy_start, end_at=busy_end)
            for bay_id, busy_start, busy_end in result.all()
        ]

    async def list_for_client(
        self,
        client_id: uuid.UUID,
        *,
        upcoming: bool,
        now: datetime,
        page: PageParams,
    ) -> tuple[Sequence[Appointment], int]:
        is_upcoming: ColumnElement[bool] = Appointment.status.in_(ACTIVE_APPOINTMENT_STATUSES) & (
            Appointment.end_at >= now
        )
        scope_condition = is_upcoming if upcoming else ~is_upcoming
        order = Appointment.start_at.asc() if upcoming else Appointment.start_at.desc()
        items, total = await fetch_page(
            self._session,
            select(Appointment).options(*DETAIL_OPTIONS),
            [Appointment.client_id == client_id, scope_condition],
            [order, Appointment.id.asc()],
            page,
        )
        return items, total

    async def list_for_workshop(
        self,
        workshop_id: uuid.UUID,
        start_at: datetime,
        end_at: datetime,
    ) -> Sequence[Appointment]:
        result = await self._session.execute(
            select(Appointment)
            .options(*DETAIL_OPTIONS)
            .where(
                Appointment.workshop_id == workshop_id,
                Appointment.start_at < end_at,
                Appointment.end_at > start_at,
            )
            .order_by(Appointment.start_at, Appointment.id)
        )
        return result.unique().scalars().all()

    async def claim_due_reminders(
        self,
        *,
        now: datetime,
        until: datetime,
        limit: int,
    ) -> Sequence[Appointment]:
        result = await self._session.execute(
            select(Appointment)
            .options(*DETAIL_OPTIONS)
            .where(
                Appointment.status == AppointmentStatus.SCHEDULED,
                Appointment.reminder_sent_at.is_(None),
                Appointment.start_at > now,
                Appointment.start_at <= until,
            )
            .order_by(Appointment.start_at)
            .limit(limit)
            .with_for_update(skip_locked=True, of=Appointment)
        )
        return result.unique().scalars().all()
