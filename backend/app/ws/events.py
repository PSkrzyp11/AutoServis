import uuid
from enum import StrEnum
from typing import Protocol

from pydantic import BaseModel
from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.core.logging import get_logger

CHANNEL_PREFIX = "realtime"
CHANNEL_PATTERN = f"{CHANNEL_PREFIX}:*"

logger = get_logger()


class RealtimeEventType(StrEnum):
    ORDER_CHANGED = "order.changed"
    APPOINTMENT_CHANGED = "appointment.changed"
    NOTIFICATION_CREATED = "notification.created"


class RealtimeEvent(BaseModel):
    type: RealtimeEventType
    entity_id: uuid.UUID
    workshop_id: uuid.UUID | None = None


def workshop_channel(workshop_id: uuid.UUID) -> str:
    return f"{CHANNEL_PREFIX}:workshop:{workshop_id}"


def user_channel(user_id: uuid.UUID) -> str:
    return f"{CHANNEL_PREFIX}:user:{user_id}"


class EventPublisher(Protocol):
    async def publish(self, channel: str, event: RealtimeEvent) -> None: ...


class RedisEventPublisher:
    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    async def publish(self, channel: str, event: RealtimeEvent) -> None:
        try:
            await self._redis.publish(channel, event.model_dump_json())
        except RedisError:
            logger.warning("realtime_publish_failed", channel=channel, event_type=event.type.value)
