import uuid
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime

from sqlalchemy import ColumnElement, exists, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import InstrumentedAttribute, joinedload, selectinload
from sqlalchemy.orm.interfaces import LoaderOption

from app.models.appointment import Appointment
from app.models.enums import CLOSED_ORDER_STATUSES, OrderStatus
from app.models.service_order import OrderStatusHistory, ServiceOrder
from app.repositories.query_helpers import fetch_page
from app.schemas.order import OrderSortField
from app.schemas.pagination import PageParams, SortOrder

SUMMARY_OPTIONS: tuple[LoaderOption, ...] = (
    joinedload(ServiceOrder.appointment).options(
        joinedload(Appointment.vehicle),
        joinedload(Appointment.client),
        joinedload(Appointment.service_type),
        joinedload(Appointment.bay),
        joinedload(Appointment.workshop),
    ),
    joinedload(ServiceOrder.mechanic),
)
DETAIL_OPTIONS: tuple[LoaderOption, ...] = (
    *SUMMARY_OPTIONS,
    selectinload(ServiceOrder.history).joinedload(OrderStatusHistory.changed_by),
)
SORT_COLUMNS: dict[OrderSortField, InstrumentedAttribute[object]] = {
    OrderSortField.NUMBER: ServiceOrder.number,
    OrderSortField.CREATED_AT: ServiceOrder.created_at,
    OrderSortField.STATUS_CHANGED_AT: ServiceOrder.status_changed_at,
}


@dataclass(frozen=True)
class OrderFilters:
    statuses: Sequence[OrderStatus] = field(default_factory=tuple)
    mechanic_id: uuid.UUID | None = None
    unassigned: bool = False


@dataclass(frozen=True)
class OrderSorting:
    field: OrderSortField = OrderSortField.CREATED_AT
    order: SortOrder = SortOrder.DESC


class OrderRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def add(self, order: ServiceOrder) -> None:
        self._session.add(order)

    def add_history(self, entry: OrderStatusHistory) -> None:
        self._session.add(entry)

    async def get_for_update(self, order_id: uuid.UUID) -> ServiceOrder | None:
        result = await self._session.execute(
            select(ServiceOrder).where(ServiceOrder.id == order_id).with_for_update()
        )
        return result.scalar_one_or_none()

    async def get_detailed(self, order_id: uuid.UUID) -> ServiceOrder | None:
        result = await self._session.execute(
            select(ServiceOrder)
            .options(*DETAIL_OPTIONS)
            .where(ServiceOrder.id == order_id)
            .execution_options(populate_existing=True)
        )
        return result.unique().scalar_one_or_none()

    async def get_detailed_for_client(
        self,
        client_id: uuid.UUID,
        order_id: uuid.UUID,
    ) -> ServiceOrder | None:
        result = await self._session.execute(
            select(ServiceOrder)
            .join(ServiceOrder.appointment)
            .options(*DETAIL_OPTIONS)
            .where(ServiceOrder.id == order_id, Appointment.client_id == client_id)
        )
        return result.unique().scalar_one_or_none()

    async def list_board(
        self,
        workshop_id: uuid.UUID,
        closed_since: datetime,
    ) -> Sequence[ServiceOrder]:
        result = await self._session.execute(
            select(ServiceOrder)
            .options(*SUMMARY_OPTIONS)
            .where(
                ServiceOrder.workshop_id == workshop_id,
                or_(
                    ServiceOrder.status.not_in(CLOSED_ORDER_STATUSES),
                    ServiceOrder.closed_at >= closed_since,
                ),
            )
            .order_by(ServiceOrder.status_changed_at, ServiceOrder.number)
        )
        return result.scalars().all()

    async def search(
        self,
        workshop_id: uuid.UUID,
        filters: OrderFilters,
        sorting: OrderSorting,
        page: PageParams,
    ) -> tuple[Sequence[ServiceOrder], int]:
        conditions: list[ColumnElement[bool]] = [ServiceOrder.workshop_id == workshop_id]
        if filters.statuses:
            conditions.append(ServiceOrder.status.in_(filters.statuses))
        if filters.mechanic_id is not None:
            conditions.append(ServiceOrder.mechanic_id == filters.mechanic_id)
        if filters.unassigned:
            conditions.append(ServiceOrder.mechanic_id.is_(None))
        column = SORT_COLUMNS[sorting.field]
        order = column.asc() if sorting.order is SortOrder.ASC else column.desc()
        return await fetch_page(
            self._session,
            select(ServiceOrder).options(*SUMMARY_OPTIONS),
            conditions,
            [order, ServiceOrder.number.desc()],
            page,
        )

    async def list_for_client(
        self,
        client_id: uuid.UUID,
        *,
        closed: bool,
        page: PageParams,
    ) -> tuple[Sequence[ServiceOrder], int]:
        is_closed = ServiceOrder.status.in_(CLOSED_ORDER_STATUSES)
        return await fetch_page(
            self._session,
            select(ServiceOrder).join(ServiceOrder.appointment).options(*SUMMARY_OPTIONS),
            [Appointment.client_id == client_id, is_closed if closed else ~is_closed],
            [ServiceOrder.created_at.desc(), ServiceOrder.number.desc()],
            page,
        )

    async def workshop_has_orders(self, workshop_id: uuid.UUID) -> bool:
        result = await self._session.scalar(
            select(exists().where(ServiceOrder.workshop_id == workshop_id))
        )
        return bool(result)
