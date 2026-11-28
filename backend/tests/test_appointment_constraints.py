import uuid
from dataclasses import dataclass
from datetime import timedelta

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.time import utc_now
from app.models.appointment import Appointment
from app.models.enums import AppointmentStatus
from app.models.workshop import Workshop
from app.services.appointment_service import (
    BAY_CONSTRAINT,
    VEHICLE_CONSTRAINT,
    violated_constraint,
)
from tests.factories import (
    create_bay,
    create_service_type,
    create_user,
    create_vehicle,
    create_workshop,
)


@dataclass
class ExistingBooking:
    workshop: Workshop
    appointment: Appointment


@pytest.fixture
async def existing(db_session: AsyncSession) -> ExistingBooking:
    workshop = await create_workshop(db_session)
    bay = await create_bay(db_session, workshop, name="Podnośnik A")
    service_type = await create_service_type(db_session, workshop)
    owner = await create_user(db_session)
    vehicle = await create_vehicle(db_session, owner)
    start_at = utc_now() + timedelta(days=1)
    appointment = Appointment(
        workshop_id=workshop.id,
        bay_id=bay.id,
        vehicle_id=vehicle.id,
        client_id=owner.id,
        service_type_id=service_type.id,
        start_at=start_at,
        end_at=start_at + timedelta(hours=1),
        status=AppointmentStatus.SCHEDULED,
    )
    db_session.add(appointment)
    await db_session.commit()
    return ExistingBooking(workshop=workshop, appointment=appointment)


def shifted_copy(
    original: Appointment,
    *,
    shift: timedelta,
    bay_id: uuid.UUID | None = None,
    vehicle_id: uuid.UUID | None = None,
    status: AppointmentStatus = AppointmentStatus.SCHEDULED,
) -> Appointment:
    start_at = original.start_at + shift
    return Appointment(
        workshop_id=original.workshop_id,
        bay_id=bay_id or original.bay_id,
        vehicle_id=vehicle_id or original.vehicle_id,
        client_id=original.client_id,
        service_type_id=original.service_type_id,
        start_at=start_at,
        end_at=start_at + timedelta(hours=1),
        status=status,
    )


async def test_database_rejects_overlap_on_same_bay(
    db_session: AsyncSession,
    existing: ExistingBooking,
) -> None:
    other_owner = await create_user(db_session, email="inny@example.com")
    other_vehicle = await create_vehicle(db_session, other_owner, plate_number="KR4F21C")

    with pytest.raises(IntegrityError) as error:
        async with db_session.begin_nested():
            db_session.add(
                shifted_copy(
                    existing.appointment,
                    shift=timedelta(minutes=30),
                    vehicle_id=other_vehicle.id,
                )
            )

    assert violated_constraint(error.value) == BAY_CONSTRAINT


async def test_database_rejects_overlap_of_same_vehicle(
    db_session: AsyncSession,
    existing: ExistingBooking,
) -> None:
    other_bay = await create_bay(db_session, existing.workshop, name="Podnośnik B")

    with pytest.raises(IntegrityError) as error:
        async with db_session.begin_nested():
            db_session.add(
                shifted_copy(existing.appointment, shift=timedelta(minutes=15), bay_id=other_bay.id)
            )

    assert violated_constraint(error.value) == VEHICLE_CONSTRAINT


async def test_adjacent_and_cancelled_appointments_do_not_conflict(
    db_session: AsyncSession,
    existing: ExistingBooking,
) -> None:
    db_session.add(shifted_copy(existing.appointment, shift=timedelta(hours=1)))
    db_session.add(
        shifted_copy(
            existing.appointment,
            shift=timedelta(minutes=30),
            status=AppointmentStatus.CANCELLED,
        )
    )
    await db_session.commit()
