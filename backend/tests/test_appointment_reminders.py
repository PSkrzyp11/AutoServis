from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.email import EmailRenderer
from app.core.time import utc_now
from app.models.appointment import Appointment
from app.models.enums import AppointmentStatus
from app.services.appointment_service import AppointmentReminderService
from app.workers.tasks import send_due_appointment_reminders, send_email
from tests.factories import (
    create_bay,
    create_service_type,
    create_user,
    create_vehicle,
    create_workshop,
)
from tests.fakes import FakeEmailSender

EN_DASH = chr(0x2013)


async def create_appointment_starting_in(
    db_session: AsyncSession,
    hours: int,
    *,
    plate_number: str,
    email: str,
) -> Appointment:
    workshop = await create_workshop(db_session, name=f"Serwis {plate_number}")
    bay = await create_bay(db_session, workshop, name="Podnośnik A")
    service_type = await create_service_type(db_session, workshop)
    owner = await create_user(db_session, email=email, full_name="Magdalena Jankowska")
    vehicle = await create_vehicle(db_session, owner, plate_number=plate_number)
    start_at = utc_now() + timedelta(hours=hours)
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
    return appointment


async def test_due_reminders_are_claimed_once(
    db_session: AsyncSession,
    settings: Settings,
) -> None:
    due = await create_appointment_starting_in(
        db_session, 20, plate_number="WA10001", email="jutro@example.com"
    )
    await create_appointment_starting_in(
        db_session, 72, plate_number="WA10002", email="pozniej@example.com"
    )
    service = AppointmentReminderService(db_session, settings)

    first = await service.claim_due_reminders()
    second = await service.claim_due_reminders()

    assert [reminder["recipient"] for reminder in first] == ["jutro@example.com"]
    assert second == []
    assert due.reminder_sent_at is not None


async def test_reminder_task_renders_and_sends_polish_email(
    db_session: AsyncSession,
    settings: Settings,
) -> None:
    await create_appointment_starting_in(
        db_session, 20, plate_number="WA10001", email="jutro@example.com"
    )
    sender = FakeEmailSender()

    @asynccontextmanager
    async def shared_session() -> AsyncIterator[AsyncSession]:
        yield db_session

    sent = await send_due_appointment_reminders(
        {
            "settings": settings,
            "session_factory": shared_session,
            "email_renderer": EmailRenderer(),
            "email_sender": sender,
        }
    )

    assert sent == 1
    email = sender.sent[0].email
    assert email.subject.startswith("Przypomnienie: wizyta")
    assert "Cześć Magdalena Jankowska" in email.text_body
    assert "Toyota Corolla, WA10001" in email.html_body


async def test_generic_email_task_renders_confirmation() -> None:
    sender = FakeEmailSender()
    context = {
        "full_name": "Piotr Mazur",
        "workshop_name": "Auto Serwis Mokotów",
        "workshop_address": "ul. Puławska 145, 02-715 Warszawa",
        "workshop_phone": "+48 22 123 45 67",
        "service_name": "Wymiana oleju",
        "vehicle": "Skoda Octavia, WE3K721",
        "date": "07.12.2026",
        "start_time": "10:00",
        "end_time": "11:00",
    }

    await send_email(
        {"email_renderer": EmailRenderer(), "email_sender": sender},
        template="appointment_confirmation",
        recipient="piotr.mazur@example.com",
        context=context,
    )

    email = sender.sent[0].email
    assert email.subject == f"Potwierdzenie wizyty 07.12.2026 o 10:00 {EN_DASH} Auto Serwis Mokotów"
    assert f"10:00{EN_DASH}11:00" in email.text_body
