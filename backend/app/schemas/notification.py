import uuid
from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, Field, TypeAdapter

from app.models.enums import NotificationType, OrderStatus
from app.models.notification import Notification


class OrderStatusChangedPayload(BaseModel):
    order_id: uuid.UUID
    order_number: int
    workshop_name: str
    vehicle: str = Field(description="Make, model and plate number")
    from_status: OrderStatus | None
    to_status: OrderStatus


class OrderAssignedPayload(BaseModel):
    order_id: uuid.UUID
    order_number: int
    workshop_id: uuid.UUID
    vehicle: str = Field(description="Make, model and plate number")
    assigned_by: str = Field(description="Full name of the person who assigned the order")


class NotificationBase(BaseModel):
    id: uuid.UUID
    read_at: datetime | None
    created_at: datetime


class OrderStatusChangedNotification(NotificationBase):
    type: Literal[NotificationType.ORDER_STATUS_CHANGED]
    payload: OrderStatusChangedPayload


class OrderAssignedNotification(NotificationBase):
    type: Literal[NotificationType.ORDER_ASSIGNED]
    payload: OrderAssignedPayload


NotificationRead = Annotated[
    OrderStatusChangedNotification | OrderAssignedNotification,
    Field(discriminator="type"),
]

notification_adapter: TypeAdapter[NotificationRead] = TypeAdapter(NotificationRead)


def to_notification_read(notification: Notification) -> NotificationRead:
    return notification_adapter.validate_python(
        {
            "id": notification.id,
            "type": notification.type,
            "payload": notification.payload,
            "read_at": notification.read_at,
            "created_at": notification.created_at,
        }
    )


class NotificationPage(BaseModel):
    items: list[NotificationRead]
    total: int = Field(description="Total number of notifications matching the filters")
    limit: int
    offset: int
    unread_count: int = Field(description="Number of unread notifications of the user")


class UnreadNotificationCount(BaseModel):
    unread_count: int


class RealtimeTicketRead(BaseModel):
    ticket: str = Field(description="One-time ticket for the realtime WebSocket connection")
    expires_in_seconds: int
