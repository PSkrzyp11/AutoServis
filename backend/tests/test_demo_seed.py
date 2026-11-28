from dataclasses import asdict
from decimal import Decimal

import pytest
from pydantic import SecretStr
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.cli import resolve_demo_password
from app.core.config import Environment, Settings
from app.models.enums import OrderStatus
from app.models.service_order import OrderStatusHistory, ServiceOrder
from app.models.service_type import ServiceType
from app.models.workshop import Workshop
from app.seed.demo_seeder import DemoSeeder, adjusted_price
from app.seed.schemas import load_seed_data
from app.services.workshop_service import WorkshopPermission, WorkshopService

DEMO_PASSWORD = "Demo-haslo-testowe-1"


async def test_demo_seed_is_idempotent(db_session: AsyncSession) -> None:
    data = load_seed_data()

    first_run = await DemoSeeder(db_session, DEMO_PASSWORD).run(data)
    second_run = await DemoSeeder(db_session, DEMO_PASSWORD).run(data)

    assert first_run.workshops_created == len(data.workshops)
    assert first_run.vehicles_created == sum(len(client.vehicles) for client in data.clients)
    assert first_run.memberships_created == sum(len(item.staff) for item in data.workshops)
    assert first_run.orders_created == len(data.orders)
    assert all(count == 0 for count in asdict(second_run).values())


async def test_demo_staff_can_access_their_workshop(db_session: AsyncSession) -> None:
    data = load_seed_data()
    await DemoSeeder(db_session, DEMO_PASSWORD).run(data)
    workshop = await db_session.scalar(select(Workshop).where(Workshop.city == "Kraków"))
    assert workshop is not None
    manager = await WorkshopService(db_session).list_members(workshop)

    accessible = await WorkshopService(db_session).get_accessible_workshop(
        manager[0].user,
        workshop.id,
        WorkshopPermission.MANAGE,
    )

    assert accessible.id == workshop.id


async def test_demo_prices_follow_workshop_adjustment(db_session: AsyncSession) -> None:
    await DemoSeeder(db_session, DEMO_PASSWORD).run(load_seed_data())

    cheapest_in_krakow = await db_session.scalar(
        select(func.min(ServiceType.base_price_net))
        .join(Workshop, Workshop.id == ServiceType.workshop_id)
        .where(Workshop.city == "Kraków")
    )

    assert cheapest_in_krakow == Decimal("116.10")
    assert adjusted_price(Decimal("129.00"), -10) == Decimal("116.10")


def test_demo_password_is_required_and_blocked_in_production(settings: Settings) -> None:
    with pytest.raises(RuntimeError, match="DEMO_USER_PASSWORD"):
        resolve_demo_password(settings.model_copy(update={"demo_user_password": None}))

    production = settings.model_copy(
        update={"app_env": Environment.PRODUCTION, "demo_user_password": SecretStr(DEMO_PASSWORD)}
    )
    with pytest.raises(RuntimeError, match="production"):
        resolve_demo_password(production)

    allowed = settings.model_copy(update={"demo_user_password": SecretStr(DEMO_PASSWORD)})
    assert resolve_demo_password(allowed) == DEMO_PASSWORD


async def test_demo_orders_cover_every_status_with_history(db_session: AsyncSession) -> None:
    await DemoSeeder(db_session, DEMO_PASSWORD).run(load_seed_data())

    statuses = set(await db_session.scalars(select(ServiceOrder.status)))
    history_counts = await db_session.execute(
        select(ServiceOrder.status, func.count(OrderStatusHistory.id))
        .join(OrderStatusHistory, OrderStatusHistory.order_id == ServiceOrder.id)
        .group_by(ServiceOrder.id, ServiceOrder.status)
    )
    closed_without_date = await db_session.scalar(
        select(func.count())
        .select_from(ServiceOrder)
        .where(
            ServiceOrder.status.in_([OrderStatus.COMPLETED, OrderStatus.CANCELLED]),
            ServiceOrder.closed_at.is_(None),
        )
    )

    assert statuses == set(OrderStatus)
    counts = dict(history_counts.all())
    assert counts[OrderStatus.RECEIVED] == 1
    assert counts[OrderStatus.COMPLETED] == 6
    assert closed_without_date == 0
