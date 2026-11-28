import asyncio
import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import timedelta

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.core.config import Settings
from app.core.errors import AppError
from app.core.time import utc_now
from app.models.appointment import Appointment
from app.models.enums import AppointmentStatus, OrderStatus, UserRole
from app.models.service_order import ServiceOrder
from app.models.user import User
from app.models.workshop import Workshop
from app.schemas.order import OrderStatusChange
from app.services.order_service import OrderService
from app.services.outbox import Outbox
from tests.factories import (
    assign_member,
    create_bay,
    create_service_type,
    create_user,
    create_vehicle,
    create_workshop,
)
from tests.fakes import FakeEventPublisher, FakeTaskQueue

CLEANUP_STATEMENT = text("TRUNCATE users, workshops RESTART IDENTITY CASCADE")


@dataclass
class CommittedOrder:
    workshop: Workshop
    managers: list[User]
    order_id: uuid.UUID


@pytest.fixture
async def session_factory(engine: AsyncEngine) -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    factory = async_sessionmaker(engine, expire_on_commit=False)
    yield factory
    async with engine.begin() as connection:
        await connection.execute(CLEANUP_STATEMENT)


@pytest.fixture
async def committed(session_factory: async_sessionmaker[AsyncSession]) -> CommittedOrder:
    async with session_factory() as session:
        workshop = await create_workshop(session)
        bay = await create_bay(session, workshop, name="Podnośnik A")
        service_type = await create_service_type(session, workshop)
        managers = []
        for index in range(2):
            manager = await create_user(
                session,
                email=f"kierownik{index}@example.com",
                role=UserRole.MANAGER,
            )
            await assign_member(session, workshop, manager)
            managers.append(manager)
        owner = await create_user(session, email="klient@example.com")
        vehicle = await create_vehicle(session, owner)
        start_at = utc_now()
        appointment = Appointment(
            workshop_id=workshop.id,
            bay_id=bay.id,
            vehicle_id=vehicle.id,
            client_id=owner.id,
            service_type_id=service_type.id,
            start_at=start_at,
            end_at=start_at + timedelta(hours=1),
            status=AppointmentStatus.CHECKED_IN,
        )
        session.add(appointment)
        await session.flush()
        order = ServiceOrder(workshop_id=workshop.id, appointment_id=appointment.id)
        session.add(order)
        await session.commit()
    return CommittedOrder(workshop=workshop, managers=managers, order_id=order.id)


async def move_in_own_session(
    session_factory: async_sessionmaker[AsyncSession],
    settings: Settings,
    committed: CommittedOrder,
    actor: User,
    target: OrderStatus,
) -> str:
    async with session_factory() as session:
        service = OrderService(session, settings, Outbox(FakeEventPublisher(), FakeTaskQueue()))
        change = OrderStatusChange(status=target, expected_status=OrderStatus.RECEIVED)
        try:
            await service.change_status(committed.workshop, actor, committed.order_id, change)
        except AppError as error:
            return error.code.value
        return target.value


async def test_parallel_status_changes_end_with_one_winner(
    session_factory: async_sessionmaker[AsyncSession],
    settings: Settings,
    committed: CommittedOrder,
) -> None:
    targets = [OrderStatus.DIAGNOSIS, OrderStatus.CANCELLED]

    outcomes = await asyncio.gather(
        *(
            move_in_own_session(session_factory, settings, committed, actor, target)
            for actor, target in zip(committed.managers, targets, strict=True)
        )
    )

    assert "ORDER_STATUS_CONFLICT" in outcomes
    winners = [outcome for outcome in outcomes if outcome != "ORDER_STATUS_CONFLICT"]
    assert len(winners) == 1
    async with session_factory() as session:
        history_count = await session.scalar(text("SELECT count(*) FROM order_status_history"))
        stored_status = await session.scalar(text("SELECT status FROM service_orders"))
    assert history_count == 1
    assert stored_status == winners[0]
