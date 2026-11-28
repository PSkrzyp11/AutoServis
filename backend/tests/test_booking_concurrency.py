import asyncio
from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import UTC, datetime, time, timedelta
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.core.config import Settings
from app.core.errors import AppError
from app.core.time import utc_now
from app.models.user import User
from app.models.vehicle import Vehicle
from app.models.workshop import Workshop
from app.schemas.appointment import AppointmentCreate
from app.services.appointment_service import AppointmentService
from tests.factories import (
    create_bay,
    create_service_type,
    create_user,
    create_vehicle,
    create_workshop,
    open_every_day,
)
from tests.fakes import FakeTaskQueue

WARSAW = ZoneInfo("Europe/Warsaw")
CLEANUP_STATEMENT = text("TRUNCATE users, workshops RESTART IDENTITY CASCADE")
CONCURRENT_CLIENTS = 2


@dataclass
class CommittedSetup:
    workshop: Workshop
    service_type_id: object
    clients: list[tuple[User, Vehicle]]


@pytest.fixture
async def session_factory(engine: AsyncEngine) -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    factory = async_sessionmaker(engine, expire_on_commit=False)
    yield factory
    async with engine.begin() as connection:
        await connection.execute(CLEANUP_STATEMENT)


@pytest.fixture
async def committed(session_factory: async_sessionmaker[AsyncSession]) -> CommittedSetup:
    async with session_factory() as session:
        workshop = await create_workshop(session)
        await open_every_day(session, workshop)
        await create_bay(session, workshop, name="Jedyny podnośnik")
        service_type = await create_service_type(session, workshop)
        clients = []
        for index in range(CONCURRENT_CLIENTS):
            user = await create_user(session, email=f"klient{index}@example.com")
            vehicle = await create_vehicle(session, user, plate_number=f"WA1000{index}")
            clients.append((user, vehicle))
    return CommittedSetup(workshop=workshop, service_type_id=service_type.id, clients=clients)


async def book_in_own_session(
    session_factory: async_sessionmaker[AsyncSession],
    settings: Settings,
    client: User,
    payload: AppointmentCreate,
) -> str:
    async with session_factory() as session:
        service = AppointmentService(session, settings, FakeTaskQueue())
        try:
            await service.book(client, payload)
        except AppError as error:
            return error.code.value
        return "BOOKED"


async def test_parallel_bookings_of_last_free_slot_end_with_one_winner(
    session_factory: async_sessionmaker[AsyncSession],
    settings: Settings,
    committed: CommittedSetup,
) -> None:
    day = (utc_now().astimezone(WARSAW) + timedelta(days=3)).date()
    start_at = datetime.combine(day, time(10), tzinfo=WARSAW).astimezone(UTC)
    payloads = [
        AppointmentCreate.model_validate(
            {
                "workshop_id": committed.workshop.id,
                "service_type_id": committed.service_type_id,
                "vehicle_id": vehicle.id,
                "start_at": start_at,
            }
        )
        for _, vehicle in committed.clients
    ]

    outcomes = await asyncio.gather(
        *(
            book_in_own_session(session_factory, settings, client, payload)
            for (client, _), payload in zip(committed.clients, payloads, strict=True)
        )
    )

    assert sorted(outcomes) == ["APPOINTMENT_SLOT_TAKEN", "BOOKED"]
    async with session_factory() as session:
        stored = await session.scalar(text("SELECT count(*) FROM appointments"))
    assert stored == 1
