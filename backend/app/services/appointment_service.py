import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from fastapi import status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.email import EmailTemplate
from app.core.errors import AppError, ConflictError, ErrorCode, NotFoundError
from app.core.logging import get_logger
from app.core.time import utc_now
from app.models.appointment import Appointment
from app.models.enums import AppointmentStatus
from app.models.service_type import ServiceType
from app.models.user import User
from app.models.workshop import Workshop
from app.repositories.appointment_repository import AppointmentRepository
from app.repositories.vehicle_repository import VehicleRepository
from app.repositories.workshop_repository import WorkshopRepository
from app.repositories.workshop_resource_repository import BayRepository, ServiceTypeRepository
from app.repositories.workshop_schedule_repository import WorkshopScheduleRepository
from app.schemas.appointment import AppointmentCreate, AppointmentScope
from app.schemas.pagination import PageParams
from app.services.appointment_notifications import build_appointment_email_context
from app.services.availability import (
    AvailabilityRequest,
    AvailableSlot,
    OpeningWindow,
    compute_available_slots,
    local_day_bounds,
)
from app.services.order_service import OrderService
from app.services.outbox import Outbox
from app.workers.queue import TaskQueue
from app.ws.events import RealtimeEvent, RealtimeEventType, workshop_channel

BAY_CONSTRAINT = "ex_appointments_bay_id_period"
VEHICLE_CONSTRAINT = "ex_appointments_vehicle_id_period"
MAX_CALENDAR_RANGE_DAYS = 31
REMINDER_BATCH_SIZE = 100

ALLOWED_STAFF_TRANSITIONS: dict[AppointmentStatus, frozenset[AppointmentStatus]] = {
    AppointmentStatus.SCHEDULED: frozenset(
        {AppointmentStatus.CHECKED_IN, AppointmentStatus.NO_SHOW, AppointmentStatus.CANCELLED}
    ),
    AppointmentStatus.CHECKED_IN: frozenset(),
    AppointmentStatus.CANCELLED: frozenset(),
    AppointmentStatus.NO_SHOW: frozenset(),
}

logger = get_logger()


@dataclass(frozen=True)
class DayAvailabilityResult:
    day: date
    service_type: ServiceType
    slots: list[AvailableSlot]


def violated_constraint(error: IntegrityError) -> str | None:
    cause = getattr(error.orig, "__cause__", None)
    constraint_name = getattr(cause, "constraint_name", None)
    return constraint_name if isinstance(constraint_name, str) else None


def invalid_transition_error(
    current: AppointmentStatus,
    target: AppointmentStatus,
    reason: str | None = None,
) -> AppError:
    details: dict[str, str] = {"from": current.value, "to": target.value}
    if reason is not None:
        details["reason"] = reason
    return AppError(
        ErrorCode.INVALID_STATUS_TRANSITION,
        f"Appointment cannot change status from {current.value} to {target.value}",
        status_code=status.HTTP_409_CONFLICT,
        details=dict(details),
    )


class AppointmentService:
    def __init__(
        self,
        session: AsyncSession,
        settings: Settings,
        task_queue: TaskQueue,
        outbox: Outbox,
    ) -> None:
        self._session = session
        self._settings = settings
        self._task_queue = task_queue
        self._outbox = outbox
        self._orders = OrderService(session, settings, outbox)
        self._appointments = AppointmentRepository(session)
        self._workshops = WorkshopRepository(session)
        self._schedule = WorkshopScheduleRepository(session)
        self._bays = BayRepository(session)
        self._service_types = ServiceTypeRepository(session)
        self._vehicles = VehicleRepository(session)

    async def get_availability(
        self,
        workshop_id: uuid.UUID,
        service_type_id: uuid.UUID,
        day: date,
    ) -> DayAvailabilityResult:
        workshop = await self._get_active_workshop(workshop_id)
        service_type = await self._get_bookable_service(workshop, service_type_id)
        slots = await self._compute_slots(workshop, service_type, day, utc_now(), include_busy=True)
        return DayAvailabilityResult(day=day, service_type=service_type, slots=slots)

    async def book(self, client: User, data: AppointmentCreate) -> Appointment:
        now = utc_now()
        workshop = await self._get_active_workshop(data.workshop_id)
        service_type = await self._get_bookable_service(workshop, data.service_type_id)
        vehicle = await self._vehicles.get_for_owner(client.id, data.vehicle_id)
        if vehicle is None:
            raise NotFoundError("Vehicle not found")

        slot = await self._resolve_slot(workshop, service_type, data.start_at, now)
        reminder_sent_at = (
            now if slot.start_at - now <= self._settings.appointment_reminder_window else None
        )
        for bay_id in slot.free_bay_ids:
            appointment = Appointment(
                workshop_id=workshop.id,
                bay_id=bay_id,
                vehicle_id=vehicle.id,
                client_id=client.id,
                service_type_id=service_type.id,
                start_at=slot.start_at,
                end_at=slot.end_at,
                status=AppointmentStatus.SCHEDULED,
                problem_description=data.problem_description,
                reminder_sent_at=reminder_sent_at,
            )
            if await self._try_insert(appointment):
                self._stage_appointment_event(appointment)
                await self._session.commit()
                await self._outbox.flush()
                return await self._finalize_booking(appointment)
        raise self._slot_taken_error()

    async def list_for_client(
        self,
        client: User,
        scope: AppointmentScope,
        page: PageParams,
    ) -> tuple[Sequence[Appointment], int]:
        return await self._appointments.list_for_client(
            client.id,
            upcoming=scope is AppointmentScope.UPCOMING,
            now=utc_now(),
            page=page,
        )

    async def cancel_by_client(self, client: User, appointment_id: uuid.UUID) -> Appointment:
        now = utc_now()
        appointment = await self._appointments.get_for_update(appointment_id)
        if appointment is None or appointment.client_id != client.id:
            raise NotFoundError("Appointment not found")
        if appointment.status is not AppointmentStatus.SCHEDULED:
            raise invalid_transition_error(appointment.status, AppointmentStatus.CANCELLED)
        if appointment.start_at - now < self._settings.client_cancellation_deadline:
            raise AppError(
                ErrorCode.CANCELLATION_TOO_LATE,
                "The appointment can no longer be cancelled online",
                status_code=status.HTTP_409_CONFLICT,
                details={"deadline_hours": self._settings.client_cancellation_deadline_hours},
            )
        return await self._apply_status(appointment, AppointmentStatus.CANCELLED, now, client)

    async def list_for_workshop(
        self,
        workshop: Workshop,
        from_date: date,
        to_date: date,
    ) -> Sequence[Appointment]:
        if to_date < from_date or (to_date - from_date).days >= MAX_CALENDAR_RANGE_DAYS:
            raise AppError(
                ErrorCode.VALIDATION_ERROR,
                f"Date range must be ordered and shorter than {MAX_CALENDAR_RANGE_DAYS} days",
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            )
        timezone = ZoneInfo(workshop.timezone)
        range_start, _ = local_day_bounds(from_date, timezone)
        _, range_end = local_day_bounds(to_date, timezone)
        return await self._appointments.list_for_workshop(workshop.id, range_start, range_end)

    async def change_status_by_staff(
        self,
        workshop: Workshop,
        actor: User,
        appointment_id: uuid.UUID,
        target: AppointmentStatus,
    ) -> Appointment:
        now = utc_now()
        appointment = await self._appointments.get_for_update(appointment_id)
        if appointment is None or appointment.workshop_id != workshop.id:
            raise NotFoundError("Appointment not found")
        if target not in ALLOWED_STAFF_TRANSITIONS[appointment.status]:
            raise invalid_transition_error(appointment.status, target)
        if target is AppointmentStatus.NO_SHOW and appointment.start_at > now:
            raise invalid_transition_error(appointment.status, target, "appointment_not_started")
        return await self._apply_status(appointment, target, now, actor)

    async def _apply_status(
        self,
        appointment: Appointment,
        target: AppointmentStatus,
        now: datetime,
        actor: User,
    ) -> Appointment:
        appointment.status = target
        if target is AppointmentStatus.CANCELLED:
            appointment.cancelled_at = now
        if target is AppointmentStatus.CHECKED_IN:
            await self._session.flush()
            await self._orders.stage_opening(appointment, actor)
        self._stage_appointment_event(appointment)
        await self._session.commit()
        await self._outbox.flush()
        logger.info(
            "appointment_status_changed",
            appointment_id=str(appointment.id),
            status=target.value,
        )
        return await self._get_detailed(appointment.id)

    async def _finalize_booking(self, appointment: Appointment) -> Appointment:
        detailed = await self._get_detailed(appointment.id)
        await self._task_queue.enqueue_email(
            template=EmailTemplate.APPOINTMENT_CONFIRMATION,
            recipient=detailed.client.email,
            context=build_appointment_email_context(detailed),
        )
        logger.info(
            "appointment_booked",
            appointment_id=str(detailed.id),
            workshop_id=str(detailed.workshop_id),
            bay_id=str(detailed.bay_id),
        )
        return detailed

    async def _try_insert(self, appointment: Appointment) -> bool:
        try:
            async with self._session.begin_nested():
                self._appointments.add(appointment)
        except IntegrityError as error:
            constraint = violated_constraint(error)
            if constraint == VEHICLE_CONSTRAINT:
                raise ConflictError(
                    ErrorCode.VEHICLE_ALREADY_BOOKED,
                    "This vehicle already has an appointment at this time",
                ) from error
            if constraint == BAY_CONSTRAINT:
                return False
            raise
        return True

    async def _resolve_slot(
        self,
        workshop: Workshop,
        service_type: ServiceType,
        start_at: datetime,
        now: datetime,
    ) -> AvailableSlot:
        day = start_at.astimezone(ZoneInfo(workshop.timezone)).date()
        free_slots = await self._compute_slots(workshop, service_type, day, now, include_busy=True)
        slot = next((item for item in free_slots if item.start_at == start_at), None)
        if slot is not None:
            return slot
        offered_slots = await self._compute_slots(
            workshop,
            service_type,
            day,
            now,
            include_busy=False,
        )
        if any(item.start_at == start_at for item in offered_slots):
            raise self._slot_taken_error()
        raise ConflictError(
            ErrorCode.SLOT_NOT_AVAILABLE,
            "The workshop does not offer this time for the selected service",
        )

    async def _compute_slots(
        self,
        workshop: Workshop,
        service_type: ServiceType,
        day: date,
        now: datetime,
        *,
        include_busy: bool,
    ) -> list[AvailableSlot]:
        timezone = ZoneInfo(workshop.timezone)
        today = now.astimezone(timezone).date()
        if not today <= day <= today + timedelta(days=self._settings.booking_horizon_days):
            return []
        opening_hours = await self._schedule.list_opening_hours(workshop.id)
        entry = next((item for item in opening_hours if item.weekday == day.isoweekday()), None)
        bays = await self._bays.list_for_workshop(workshop.id, include_inactive=False)
        bay_ids = [
            bay.id
            for bay in bays
            if service_type.required_bay_type is None or bay.type is service_type.required_bay_type
        ]
        day_start, day_end = local_day_bounds(day, timezone)
        busy_intervals = (
            await self._appointments.list_busy_intervals(bay_ids, day_start, day_end)
            if include_busy
            else []
        )
        return compute_available_slots(
            AvailabilityRequest(
                day=day,
                timezone=timezone,
                opening_window=OpeningWindow(entry.opens_at, entry.closes_at) if entry else None,
                is_closed=await self._schedule.closure_exists(workshop.id, day),
                duration=timedelta(minutes=service_type.duration_minutes),
                bay_ids=bay_ids,
                busy_intervals=busy_intervals,
                earliest_start=now + self._settings.booking_lead_time,
            )
        )

    async def _get_active_workshop(self, workshop_id: uuid.UUID) -> Workshop:
        workshop = await self._workshops.get_by_id(workshop_id)
        if workshop is None or not workshop.is_active:
            raise NotFoundError("Workshop not found")
        return workshop

    async def _get_bookable_service(
        self,
        workshop: Workshop,
        service_type_id: uuid.UUID,
    ) -> ServiceType:
        service_type = await self._service_types.get(workshop.id, service_type_id)
        if service_type is None or not service_type.is_active:
            raise ConflictError(
                ErrorCode.SERVICE_NOT_AVAILABLE,
                "This service is not offered by the workshop",
            )
        return service_type

    async def _get_detailed(self, appointment_id: uuid.UUID) -> Appointment:
        appointment = await self._appointments.get_detailed(appointment_id)
        if appointment is None:
            raise NotFoundError("Appointment not found")
        return appointment

    def _stage_appointment_event(self, appointment: Appointment) -> None:
        self._outbox.add_event(
            workshop_channel(appointment.workshop_id),
            RealtimeEvent(
                type=RealtimeEventType.APPOINTMENT_CHANGED,
                entity_id=appointment.id,
                workshop_id=appointment.workshop_id,
            ),
        )

    @staticmethod
    def _slot_taken_error() -> ConflictError:
        return ConflictError(
            ErrorCode.APPOINTMENT_SLOT_TAKEN,
            "This time has just been booked by someone else",
        )


class AppointmentReminderService:
    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        self._session = session
        self._settings = settings
        self._appointments = AppointmentRepository(session)

    async def claim_due_reminders(self) -> list[dict[str, str]]:
        now = utc_now()
        appointments = await self._appointments.claim_due_reminders(
            now=now,
            until=now + self._settings.appointment_reminder_window,
            limit=REMINDER_BATCH_SIZE,
        )
        payloads = []
        for appointment in appointments:
            appointment.reminder_sent_at = now
            payloads.append(
                {
                    "recipient": appointment.client.email,
                    **build_appointment_email_context(appointment),
                }
            )
        await self._session.commit()
        return payloads
