import uuid
from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.email import EmailTemplate
from app.core.errors import NotFoundError
from app.core.time import utc_now
from app.models.enums import NotificationType, OrderStatus
from app.models.notification import Notification
from app.models.service_order import ServiceOrder
from app.models.user import User
from app.repositories.notification_repository import NotificationRepository
from app.schemas.notification import OrderAssignedPayload, OrderStatusChangedPayload
from app.schemas.pagination import PageParams
from app.services.order_notifications import build_order_email_context, describe_vehicle
from app.services.order_workflow import CLIENT_EMAIL_STATUSES
from app.services.outbox import Outbox
from app.ws.events import RealtimeEvent, RealtimeEventType, user_channel


class NotificationService:
    def __init__(self, session: AsyncSession, outbox: Outbox) -> None:
        self._session = session
        self._outbox = outbox
        self._notifications = NotificationRepository(session)

    def stage_order_status_changed(
        self,
        order: ServiceOrder,
        from_status: OrderStatus | None,
        to_status: OrderStatus,
    ) -> None:
        client = order.appointment.client
        payload = OrderStatusChangedPayload(
            order_id=order.id,
            order_number=order.number,
            workshop_name=order.appointment.workshop.name,
            vehicle=describe_vehicle(order),
            from_status=from_status,
            to_status=to_status,
        )
        self._stage(
            client.id, NotificationType.ORDER_STATUS_CHANGED, payload.model_dump(mode="json")
        )
        if to_status in CLIENT_EMAIL_STATUSES:
            self._outbox.add_email(
                EmailTemplate.ORDER_STATUS_CHANGED,
                client.email,
                build_order_email_context(order, to_status),
            )

    def stage_order_assigned(
        self, order: ServiceOrder, mechanic_id: uuid.UUID, actor: User
    ) -> None:
        payload = OrderAssignedPayload(
            order_id=order.id,
            order_number=order.number,
            workshop_id=order.workshop_id,
            vehicle=describe_vehicle(order),
            assigned_by=actor.full_name,
        )
        self._stage(mechanic_id, NotificationType.ORDER_ASSIGNED, payload.model_dump(mode="json"))

    async def list_for_user(
        self,
        user: User,
        *,
        unread_only: bool,
        page: PageParams,
    ) -> tuple[Sequence[Notification], int]:
        return await self._notifications.list_for_user(user.id, unread_only=unread_only, page=page)

    async def count_unread(self, user: User) -> int:
        return await self._notifications.count_unread(user.id)

    async def mark_read(self, user: User, notification_id: uuid.UUID) -> Notification:
        notification = await self._notifications.get_for_user(user.id, notification_id)
        if notification is None:
            raise NotFoundError("Notification not found")
        if notification.read_at is None:
            notification.read_at = utc_now()
            await self._session.commit()
        return notification

    async def mark_all_read(self, user: User) -> None:
        await self._notifications.mark_all_read(user.id, utc_now())
        await self._session.commit()

    def _stage(
        self,
        user_id: uuid.UUID,
        notification_type: NotificationType,
        payload: dict[str, object],
    ) -> None:
        notification = Notification(
            id=uuid.uuid4(),
            user_id=user_id,
            type=notification_type,
            payload=payload,
        )
        self._notifications.add(notification)
        self._outbox.add_event(
            user_channel(user_id),
            RealtimeEvent(type=RealtimeEventType.NOTIFICATION_CREATED, entity_id=notification.id),
        )
