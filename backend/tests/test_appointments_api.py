import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

import pytest
from fastapi import FastAPI, status
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.email import EmailTemplate
from app.core.time import utc_now
from app.models.appointment import Appointment
from app.models.bay import Bay
from app.models.enums import AppointmentStatus, BayType, UserRole
from app.models.service_type import ServiceType
from app.models.user import User
from app.models.vehicle import Vehicle
from app.models.workshop import Workshop, WorkshopClosure
from tests.factories import (
    assign_member,
    bearer,
    create_bay,
    create_service_type,
    create_user,
    create_vehicle,
    create_workshop,
    login,
    open_every_day,
)
from tests.fakes import FakeTaskQueue

WARSAW = ZoneInfo("Europe/Warsaw")
APPOINTMENTS_URL = "/api/v1/appointments"


@dataclass
class BookingSetup:
    workshop: Workshop
    lift: Bay
    second_lift: Bay
    tire_bay: Bay
    oil_change: ServiceType
    tire_change: ServiceType
    client: User
    vehicle: Vehicle
    client_token: str


def booking_day(days_ahead: int = 3) -> date:
    return (utc_now().astimezone(WARSAW) + timedelta(days=days_ahead)).date()


def local_iso(day: date, hour: int, minute: int = 0) -> str:
    return datetime.combine(day, time(hour, minute), tzinfo=WARSAW).astimezone(UTC).isoformat()


@pytest.fixture
async def setup(client: AsyncClient, db_session: AsyncSession) -> BookingSetup:
    workshop = await create_workshop(db_session, name="Auto Serwis Mokotów")
    await open_every_day(db_session, workshop)
    lift = await create_bay(db_session, workshop, name="Podnośnik A")
    second_lift = await create_bay(db_session, workshop, name="Podnośnik B")
    tire_bay = await create_bay(db_session, workshop, name="Wulkanizacja", bay_type=BayType.TIRES)
    oil_change = await create_service_type(
        db_session,
        workshop,
        required_bay_type=BayType.LIFT,
    )
    tire_change = await create_service_type(
        db_session,
        workshop,
        name="Wymiana opon",
        duration_minutes=45,
        required_bay_type=BayType.TIRES,
    )
    client_user = await create_user(db_session, email="magdalena.jankowska@example.com")
    vehicle = await create_vehicle(db_session, client_user)
    return BookingSetup(
        workshop=workshop,
        lift=lift,
        second_lift=second_lift,
        tire_bay=tire_bay,
        oil_change=oil_change,
        tire_change=tire_change,
        client=client_user,
        vehicle=vehicle,
        client_token=await login(client, client_user.email),
    )


def booking_payload(
    setup: BookingSetup,
    start_at: str,
    *,
    vehicle_id: uuid.UUID | None = None,
    service_type: ServiceType | None = None,
) -> dict[str, object]:
    return {
        "workshop_id": str(setup.workshop.id),
        "service_type_id": str((service_type or setup.oil_change).id),
        "vehicle_id": str(vehicle_id or setup.vehicle.id),
        "start_at": start_at,
        "problem_description": "Stuka przy skręcie w prawo",
    }


async def second_client(
    client: AsyncClient,
    db_session: AsyncSession,
    email: str,
    plate_number: str,
) -> tuple[str, Vehicle]:
    user = await create_user(db_session, email=email)
    vehicle = await create_vehicle(db_session, user, plate_number=plate_number)
    return await login(client, email), vehicle


async def insert_appointment(
    db_session: AsyncSession,
    setup: BookingSetup,
    start_at: datetime,
    *,
    status_value: AppointmentStatus = AppointmentStatus.SCHEDULED,
    reminder_sent_at: datetime | None = None,
) -> Appointment:
    appointment = Appointment(
        workshop_id=setup.workshop.id,
        bay_id=setup.lift.id,
        vehicle_id=setup.vehicle.id,
        client_id=setup.client.id,
        service_type_id=setup.oil_change.id,
        start_at=start_at,
        end_at=start_at + timedelta(hours=1),
        status=status_value,
        reminder_sent_at=reminder_sent_at,
    )
    db_session.add(appointment)
    await db_session.commit()
    return appointment


async def test_availability_lists_slots_within_opening_hours(
    client: AsyncClient,
    setup: BookingSetup,
) -> None:
    day = booking_day()

    response = await client.get(
        f"/api/v1/workshops/{setup.workshop.id}/availability",
        params={"service_type_id": str(setup.oil_change.id), "date": day.isoformat()},
    )

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["duration_minutes"] == 60
    assert len(body["slots"]) == 29
    assert datetime.fromisoformat(body["slots"][0]["start_at"]) == datetime.fromisoformat(
        local_iso(day, 8)
    )


async def test_availability_outside_horizon_is_empty(
    client: AsyncClient,
    setup: BookingSetup,
) -> None:
    response = await client.get(
        f"/api/v1/workshops/{setup.workshop.id}/availability",
        params={"service_type_id": str(setup.oil_change.id), "date": "2000-01-01"},
    )

    assert response.json()["slots"] == []


async def test_booking_assigns_bay_and_sends_confirmation(
    client: AsyncClient,
    setup: BookingSetup,
    task_queue: FakeTaskQueue,
) -> None:
    day = booking_day()

    response = await client.post(
        APPOINTMENTS_URL,
        headers=bearer(setup.client_token),
        json=booking_payload(setup, local_iso(day, 10)),
    )

    assert response.status_code == status.HTTP_201_CREATED
    body = response.json()
    assert body["status"] == "SCHEDULED"
    assert body["bay"]["name"] == "Podnośnik A"
    assert body["workshop"]["slug"] == setup.workshop.slug
    assert body["vehicle"]["plate_number"] == "WA58213"
    assert body["problem_description"] == "Stuka przy skręcie w prawo"
    job = task_queue.emails[0]
    assert job.template is EmailTemplate.APPOINTMENT_CONFIRMATION
    assert job.recipient == setup.client.email
    assert job.context["start_time"] == "10:00"
    assert job.context["date"] == day.strftime("%d.%m.%Y")


async def test_bays_fill_up_until_slot_is_taken(
    client: AsyncClient,
    db_session: AsyncSession,
    setup: BookingSetup,
) -> None:
    start_at = local_iso(booking_day(), 10)
    second_token, second_vehicle = await second_client(
        client, db_session, "piotr.mazur@example.com", "WE3K721"
    )
    third_token, third_vehicle = await second_client(
        client, db_session, "ewa.grabowska@example.com", "KR4F21C"
    )

    first = await client.post(
        APPOINTMENTS_URL,
        headers=bearer(setup.client_token),
        json=booking_payload(setup, start_at),
    )
    second = await client.post(
        APPOINTMENTS_URL,
        headers=bearer(second_token),
        json=booking_payload(setup, start_at, vehicle_id=second_vehicle.id),
    )
    third = await client.post(
        APPOINTMENTS_URL,
        headers=bearer(third_token),
        json=booking_payload(setup, start_at, vehicle_id=third_vehicle.id),
    )

    assert first.json()["bay"]["name"] == "Podnośnik A"
    assert second.json()["bay"]["name"] == "Podnośnik B"
    assert third.status_code == status.HTTP_409_CONFLICT
    assert third.json()["error"]["code"] == "APPOINTMENT_SLOT_TAKEN"


async def test_service_with_required_bay_type_uses_matching_bay_only(
    client: AsyncClient,
    setup: BookingSetup,
) -> None:
    day = booking_day()
    booked = await client.post(
        APPOINTMENTS_URL,
        headers=bearer(setup.client_token),
        json=booking_payload(setup, local_iso(day, 10), service_type=setup.tire_change),
    )

    tire_availability = await client.get(
        f"/api/v1/workshops/{setup.workshop.id}/availability",
        params={"service_type_id": str(setup.tire_change.id), "date": day.isoformat()},
    )
    oil_availability = await client.get(
        f"/api/v1/workshops/{setup.workshop.id}/availability",
        params={"service_type_id": str(setup.oil_change.id), "date": day.isoformat()},
    )

    ten_o_clock = datetime.fromisoformat(local_iso(day, 10))
    tire_starts = {datetime.fromisoformat(s["start_at"]) for s in tire_availability.json()["slots"]}
    oil_starts = {datetime.fromisoformat(s["start_at"]) for s in oil_availability.json()["slots"]}
    assert booked.json()["bay"]["name"] == "Wulkanizacja"
    assert ten_o_clock not in tire_starts
    assert ten_o_clock in oil_starts


@pytest.mark.parametrize("minute", [7, 50])
async def test_time_not_offered_is_rejected(
    client: AsyncClient,
    setup: BookingSetup,
    minute: int,
) -> None:
    hour = 10 if minute == 7 else 15
    response = await client.post(
        APPOINTMENTS_URL,
        headers=bearer(setup.client_token),
        json=booking_payload(setup, local_iso(booking_day(), hour, minute)),
    )

    assert response.json()["error"]["code"] == "SLOT_NOT_AVAILABLE"


async def test_closed_day_and_past_time_are_rejected(
    client: AsyncClient,
    db_session: AsyncSession,
    setup: BookingSetup,
) -> None:
    closed_day = booking_day(5)
    db_session.add(WorkshopClosure(workshop_id=setup.workshop.id, closed_on=closed_day))
    await db_session.commit()

    closed = await client.post(
        APPOINTMENTS_URL,
        headers=bearer(setup.client_token),
        json=booking_payload(setup, local_iso(closed_day, 10)),
    )
    past = await client.post(
        APPOINTMENTS_URL,
        headers=bearer(setup.client_token),
        json=booking_payload(setup, local_iso(booking_day(-1), 10)),
    )

    assert closed.json()["error"]["code"] == "SLOT_NOT_AVAILABLE"
    assert past.json()["error"]["code"] == "SLOT_NOT_AVAILABLE"


async def test_same_vehicle_cannot_be_booked_twice_at_overlapping_times(
    client: AsyncClient,
    setup: BookingSetup,
) -> None:
    day = booking_day()
    await client.post(
        APPOINTMENTS_URL,
        headers=bearer(setup.client_token),
        json=booking_payload(setup, local_iso(day, 10)),
    )

    response = await client.post(
        APPOINTMENTS_URL,
        headers=bearer(setup.client_token),
        json=booking_payload(setup, local_iso(day, 10, 30)),
    )

    assert response.json()["error"]["code"] == "VEHICLE_ALREADY_BOOKED"


async def test_foreign_vehicle_and_inactive_service_are_rejected(
    client: AsyncClient,
    db_session: AsyncSession,
    setup: BookingSetup,
) -> None:
    _, foreign_vehicle = await second_client(
        client, db_session, "piotr.mazur@example.com", "WE3K721"
    )
    inactive = await create_service_type(db_session, setup.workshop, name="Stara", is_active=False)
    start_at = local_iso(booking_day(), 10)

    foreign = await client.post(
        APPOINTMENTS_URL,
        headers=bearer(setup.client_token),
        json=booking_payload(setup, start_at, vehicle_id=foreign_vehicle.id),
    )
    inactive_response = await client.post(
        APPOINTMENTS_URL,
        headers=bearer(setup.client_token),
        json=booking_payload(setup, start_at, service_type=inactive),
    )

    assert foreign.status_code == status.HTTP_404_NOT_FOUND
    assert inactive_response.json()["error"]["code"] == "SERVICE_NOT_AVAILABLE"


async def test_client_lists_upcoming_and_past_appointments(
    client: AsyncClient,
    db_session: AsyncSession,
    setup: BookingSetup,
) -> None:
    await client.post(
        APPOINTMENTS_URL,
        headers=bearer(setup.client_token),
        json=booking_payload(setup, local_iso(booking_day(), 10)),
    )
    await insert_appointment(db_session, setup, utc_now() - timedelta(days=10))

    upcoming = await client.get(f"{APPOINTMENTS_URL}/mine", headers=bearer(setup.client_token))
    past = await client.get(
        f"{APPOINTMENTS_URL}/mine",
        headers=bearer(setup.client_token),
        params={"scope": "past"},
    )

    assert upcoming.json()["total"] == 1
    assert past.json()["total"] == 1
    assert past.json()["items"][0]["service_type"]["name"] == "Wymiana oleju"


async def test_client_cancels_in_time_but_not_too_late(
    client: AsyncClient,
    db_session: AsyncSession,
    setup: BookingSetup,
) -> None:
    booked = await client.post(
        APPOINTMENTS_URL,
        headers=bearer(setup.client_token),
        json=booking_payload(setup, local_iso(booking_day(), 10)),
    )
    soon = await insert_appointment(db_session, setup, utc_now() + timedelta(hours=2))

    cancelled = await client.post(
        f"{APPOINTMENTS_URL}/{booked.json()['id']}/cancel",
        headers=bearer(setup.client_token),
    )
    cancelled_again = await client.post(
        f"{APPOINTMENTS_URL}/{booked.json()['id']}/cancel",
        headers=bearer(setup.client_token),
    )
    too_late = await client.post(
        f"{APPOINTMENTS_URL}/{soon.id}/cancel",
        headers=bearer(setup.client_token),
    )

    assert cancelled.json()["status"] == "CANCELLED"
    assert cancelled.json()["cancelled_at"] is not None
    assert cancelled_again.json()["error"]["code"] == "INVALID_STATUS_TRANSITION"
    assert too_late.json()["error"]["code"] == "CANCELLATION_TOO_LATE"
    assert too_late.json()["error"]["details"] == {"deadline_hours": 12}


async def test_cancelled_slot_becomes_free_again(
    client: AsyncClient,
    db_session: AsyncSession,
    setup: BookingSetup,
) -> None:
    start_at = local_iso(booking_day(), 10)
    for bay in (setup.lift, setup.second_lift):
        bay.is_active = bay is setup.lift
    await db_session.commit()
    booked = await client.post(
        APPOINTMENTS_URL,
        headers=bearer(setup.client_token),
        json=booking_payload(setup, start_at),
    )
    await client.post(
        f"{APPOINTMENTS_URL}/{booked.json()['id']}/cancel",
        headers=bearer(setup.client_token),
    )

    rebooked = await client.post(
        APPOINTMENTS_URL,
        headers=bearer(setup.client_token),
        json=booking_payload(setup, start_at),
    )

    assert rebooked.status_code == status.HTTP_201_CREATED


async def test_staff_calendar_access_and_range_validation(
    client: AsyncClient,
    db_session: AsyncSession,
    setup: BookingSetup,
) -> None:
    day = booking_day()
    await client.post(
        APPOINTMENTS_URL,
        headers=bearer(setup.client_token),
        json=booking_payload(setup, local_iso(day, 10)),
    )
    mechanic = await create_user(db_session, email="mechanik@example.com", role=UserRole.MECHANIC)
    await assign_member(db_session, setup.workshop, mechanic)
    mechanic_token = await login(client, mechanic.email)
    url = f"/api/v1/workshops/{setup.workshop.id}/appointments"
    params = {"from_date": day.isoformat(), "to_date": day.isoformat()}

    as_mechanic = await client.get(url, headers=bearer(mechanic_token), params=params)
    as_client = await client.get(url, headers=bearer(setup.client_token), params=params)
    too_long = await client.get(
        url,
        headers=bearer(mechanic_token),
        params={"from_date": day.isoformat(), "to_date": (day + timedelta(days=40)).isoformat()},
    )

    assert as_mechanic.status_code == status.HTTP_200_OK
    assert as_mechanic.json()[0]["client"]["email"] == setup.client.email
    assert as_client.status_code == status.HTTP_403_FORBIDDEN
    assert too_long.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


async def test_staff_status_transitions(
    client: AsyncClient,
    db_session: AsyncSession,
    setup: BookingSetup,
) -> None:
    manager = await create_user(db_session, email="kierownik@example.com", role=UserRole.MANAGER)
    await assign_member(db_session, setup.workshop, manager)
    token = await login(client, manager.email)
    base_url = f"/api/v1/workshops/{setup.workshop.id}/appointments"
    future = await insert_appointment(db_session, setup, utc_now() + timedelta(days=2))
    later = await insert_appointment(db_session, setup, utc_now() + timedelta(days=3))
    started = await insert_appointment(db_session, setup, utc_now() - timedelta(hours=3))

    early_no_show = await client.post(f"{base_url}/{future.id}/no-show", headers=bearer(token))
    checked_in = await client.post(f"{base_url}/{future.id}/check-in", headers=bearer(token))
    cancel_checked_in = await client.post(f"{base_url}/{future.id}/cancel", headers=bearer(token))
    cancelled = await client.post(f"{base_url}/{later.id}/cancel", headers=bearer(token))
    after_cancel = await client.post(f"{base_url}/{later.id}/check-in", headers=bearer(token))
    no_show = await client.post(f"{base_url}/{started.id}/no-show", headers=bearer(token))
    unknown = await client.post(f"{base_url}/{uuid.uuid4()}/check-in", headers=bearer(token))

    assert early_no_show.json()["error"]["details"]["reason"] == "appointment_not_started"
    assert checked_in.json()["status"] == "CHECKED_IN"
    assert checked_in.json()["order"]["status"] == "RECEIVED"
    assert cancel_checked_in.json()["error"]["code"] == "INVALID_STATUS_TRANSITION"
    assert cancelled.json()["status"] == "CANCELLED"
    assert cancelled.json()["order"] is None
    assert after_cancel.json()["error"]["code"] == "INVALID_STATUS_TRANSITION"
    assert no_show.json()["status"] == "NO_SHOW"
    assert unknown.status_code == status.HTTP_404_NOT_FOUND


async def test_booking_within_reminder_window_skips_reminder(
    app: FastAPI,
    client: AsyncClient,
    db_session: AsyncSession,
    settings: Settings,
    setup: BookingSetup,
) -> None:
    app.dependency_overrides[get_settings] = lambda: settings.model_copy(
        update={"appointment_reminder_hours": 24 * 30}
    )

    response = await client.post(
        APPOINTMENTS_URL,
        headers=bearer(setup.client_token),
        json=booking_payload(setup, local_iso(booking_day(), 10)),
    )

    appointment = await db_session.get(Appointment, uuid.UUID(response.json()["id"]))
    assert appointment is not None
    assert appointment.reminder_sent_at is not None
