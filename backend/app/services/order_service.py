import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta

from fastapi import status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.errors import AppError, ConflictError, ErrorCode, ForbiddenError, NotFoundError
from app.core.logging import get_logger
from app.core.time import utc_now
from app.models.appointment import Appointment
from app.models.enums import STAFF_ROLES, OrderStatus, UserRole
from app.models.service_order import OrderStatusHistory, ServiceOrder
from app.models.user import User
from app.models.workshop import Workshop
from app.repositories.order_repository import OrderFilters, OrderRepository, OrderSorting
from app.repositories.user_repository import UserRepository
from app.repositories.workshop_repository import WorkshopRepository
from app.schemas.order import OrderScope, OrderStatusChange
from app.schemas.pagination import PageParams
from app.services.notification_service import NotificationService
from app.services.order_workflow import (
    STATUSES_REQUIRING_DIAGNOSIS,
    can_operate,
    is_closed,
    is_transition_allowed,
)
from app.services.outbox import Outbox
from app.ws.events import RealtimeEvent, RealtimeEventType, workshop_channel

logger = get_logger()


@dataclass(frozen=True)
class OrderBoardResult:
    orders: Sequence[ServiceOrder]
    closed_since: datetime


def order_not_found() -> NotFoundError:
    return NotFoundError("Order not found")


class OrderService:
    def __init__(self, session: AsyncSession, settings: Settings, outbox: Outbox) -> None:
        self._session = session
        self._settings = settings
        self._outbox = outbox
        self._orders = OrderRepository(session)
        self._users = UserRepository(session)
        self._workshops = WorkshopRepository(session)
        self._notifications = NotificationService(session, outbox)

    async def stage_opening(self, appointment: Appointment, actor: User) -> ServiceOrder:
        now = utc_now()
        order = ServiceOrder(
            id=uuid.uuid4(),
            workshop_id=appointment.workshop_id,
            appointment_id=appointment.id,
            status=OrderStatus.RECEIVED,
            status_changed_at=now,
        )
        self._orders.add(order)
        self._orders.add_history(
            OrderStatusHistory(
                order_id=order.id,
                from_status=None,
                to_status=OrderStatus.RECEIVED,
                changed_by_id=actor.id,
                changed_at=now,
            )
        )
        await self._session.flush()
        detailed = await self._get_detailed(order.id)
        self._notifications.stage_order_status_changed(detailed, None, OrderStatus.RECEIVED)
        self._stage_order_event(detailed)
        logger.info("order_opened", order_id=str(order.id), number=detailed.number)
        return detailed

    async def get_board(self, workshop: Workshop) -> OrderBoardResult:
        closed_since = utc_now() - timedelta(days=self._settings.order_board_closed_days)
        orders = await self._orders.list_board(workshop.id, closed_since)
        return OrderBoardResult(orders=orders, closed_since=closed_since)

    async def search(
        self,
        workshop: Workshop,
        filters: OrderFilters,
        sorting: OrderSorting,
        page: PageParams,
    ) -> tuple[Sequence[ServiceOrder], int]:
        return await self._orders.search(workshop.id, filters, sorting, page)

    async def get_for_staff(self, workshop: Workshop, order_id: uuid.UUID) -> ServiceOrder:
        order = await self._orders.get_detailed(order_id)
        if order is None or order.workshop_id != workshop.id:
            raise order_not_found()
        return order

    async def change_status(
        self,
        workshop: Workshop,
        actor: User,
        order_id: uuid.UUID,
        change: OrderStatusChange,
    ) -> ServiceOrder:
        order = await self._lock(workshop, order_id)
        if order.status is not change.expected_status:
            raise AppError(
                ErrorCode.ORDER_STATUS_CONFLICT,
                "The order status was changed by someone else",
                status_code=status.HTTP_409_CONFLICT,
                details={"current_status": order.status.value},
            )
        self._ensure_can_operate(order, actor)
        if not is_transition_allowed(order.status, change.status):
            raise AppError(
                ErrorCode.INVALID_STATUS_TRANSITION,
                f"Order cannot change status from {order.status.value} to {change.status.value}",
                status_code=status.HTTP_409_CONFLICT,
                details={"from": order.status.value, "to": change.status.value},
            )
        if change.status in STATUSES_REQUIRING_DIAGNOSIS and not order.diagnosis:
            raise ConflictError(
                ErrorCode.DIAGNOSIS_REQUIRED,
                "Describe the diagnosis before asking the client for approval",
            )

        now = utc_now()
        previous = order.status
        if order.mechanic_id is None and actor.role is UserRole.MECHANIC:
            order.mechanic_id = actor.id
        order.status = change.status
        order.status_changed_at = now
        if is_closed(change.status):
            order.closed_at = now
        self._orders.add_history(
            OrderStatusHistory(
                order_id=order.id,
                from_status=previous,
                to_status=change.status,
                changed_by_id=actor.id,
                note=change.note,
                changed_at=now,
            )
        )
        await self._session.flush()
        detailed = await self._get_detailed(order.id)
        self._notifications.stage_order_status_changed(detailed, previous, change.status)
        await self._commit_and_announce(detailed)
        logger.info(
            "order_status_changed",
            order_id=str(order.id),
            from_status=previous.value,
            to_status=change.status.value,
        )
        return await self._get_detailed(order.id)

    async def update_diagnosis(
        self,
        workshop: Workshop,
        actor: User,
        order_id: uuid.UUID,
        diagnosis: str,
    ) -> ServiceOrder:
        order = await self._lock(workshop, order_id)
        self._ensure_open(order)
        self._ensure_can_operate(order, actor)
        order.diagnosis = diagnosis
        await self._session.flush()
        await self._commit_and_announce(await self._get_detailed(order.id))
        logger.info("order_diagnosis_updated", order_id=str(order.id))
        return await self._get_detailed(order.id)

    async def assign_mechanic(
        self,
        workshop: Workshop,
        actor: User,
        order_id: uuid.UUID,
        mechanic_id: uuid.UUID | None,
    ) -> ServiceOrder:
        order = await self._lock(workshop, order_id)
        self._ensure_open(order)
        if mechanic_id is not None:
            await self._ensure_assignable(workshop, mechanic_id)
        changed = order.mechanic_id != mechanic_id
        order.mechanic_id = mechanic_id
        await self._session.flush()
        detailed = await self._get_detailed(order.id)
        if changed and mechanic_id is not None and mechanic_id != actor.id:
            self._notifications.stage_order_assigned(detailed, mechanic_id, actor)
        await self._commit_and_announce(detailed)
        logger.info(
            "order_mechanic_assigned",
            order_id=str(order.id),
            mechanic_id=str(mechanic_id) if mechanic_id else None,
        )
        return await self._get_detailed(order.id)

    async def claim(self, workshop: Workshop, actor: User, order_id: uuid.UUID) -> ServiceOrder:
        if actor.role not in STAFF_ROLES:
            raise ForbiddenError(ErrorCode.FORBIDDEN, "Only workshop staff can take orders")
        order = await self._lock(workshop, order_id)
        self._ensure_open(order)
        if order.mechanic_id == actor.id:
            return await self._get_detailed(order.id)
        if order.mechanic_id is not None:
            raise ConflictError(
                ErrorCode.ORDER_ALREADY_ASSIGNED,
                "The order is already assigned to another person",
            )
        order.mechanic_id = actor.id
        await self._session.flush()
        await self._commit_and_announce(await self._get_detailed(order.id))
        logger.info("order_claimed", order_id=str(order.id))
        return await self._get_detailed(order.id)

    async def list_for_client(
        self,
        client: User,
        scope: OrderScope,
        page: PageParams,
    ) -> tuple[Sequence[ServiceOrder], int]:
        return await self._orders.list_for_client(
            client.id,
            closed=scope is OrderScope.CLOSED,
            page=page,
        )

    async def get_for_client(self, client: User, order_id: uuid.UUID) -> ServiceOrder:
        order = await self._orders.get_detailed_for_client(client.id, order_id)
        if order is None:
            raise order_not_found()
        return order

    async def _lock(self, workshop: Workshop, order_id: uuid.UUID) -> ServiceOrder:
        order = await self._orders.get_for_update(order_id)
        if order is None or order.workshop_id != workshop.id:
            raise order_not_found()
        return order

    async def _ensure_assignable(self, workshop: Workshop, user_id: uuid.UUID) -> None:
        user = await self._users.get_by_id(user_id)
        is_staff = user is not None and user.is_active and user.role in STAFF_ROLES
        if not is_staff or not await self._workshops.is_member(user_id, workshop.id):
            raise ConflictError(
                ErrorCode.ASSIGNEE_NOT_IN_WORKSHOP,
                "Orders can be assigned only to active staff of this workshop",
            )

    async def _commit_and_announce(self, order: ServiceOrder) -> None:
        self._stage_order_event(order)
        await self._session.commit()
        await self._outbox.flush()

    async def _get_detailed(self, order_id: uuid.UUID) -> ServiceOrder:
        order = await self._orders.get_detailed(order_id)
        if order is None:
            raise order_not_found()
        return order

    def _stage_order_event(self, order: ServiceOrder) -> None:
        self._outbox.add_event(
            workshop_channel(order.workshop_id),
            RealtimeEvent(
                type=RealtimeEventType.ORDER_CHANGED,
                entity_id=order.id,
                workshop_id=order.workshop_id,
            ),
        )

    @staticmethod
    def _ensure_open(order: ServiceOrder) -> None:
        if is_closed(order.status):
            raise ConflictError(ErrorCode.ORDER_CLOSED, "Closed orders cannot be changed")

    @staticmethod
    def _ensure_can_operate(order: ServiceOrder, actor: User) -> None:
        if not can_operate(actor.role, actor.id, order.mechanic_id):
            raise ForbiddenError(
                ErrorCode.ORDER_NOT_ASSIGNED_TO_YOU,
                "Only the assigned mechanic or a manager can change this order",
            )
