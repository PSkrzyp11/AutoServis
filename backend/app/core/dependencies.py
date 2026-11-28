from collections.abc import AsyncIterator
from typing import Annotated

from arq.connections import ArqRedis
from fastapi import Depends, Request
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import Settings, get_settings
from app.services.outbox import Outbox
from app.workers.queue import ArqTaskQueue, TaskQueue
from app.ws.events import EventPublisher, RedisEventPublisher


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    session_factory: async_sessionmaker[AsyncSession] = request.app.state.session_factory
    async with session_factory() as session:
        yield session


def get_redis(request: Request) -> Redis:
    redis: Redis = request.app.state.redis
    return redis


def get_task_queue(request: Request) -> TaskQueue:
    pool: ArqRedis = request.app.state.arq_pool
    return ArqTaskQueue(pool)


SettingsDep = Annotated[Settings, Depends(get_settings)]
SessionDep = Annotated[AsyncSession, Depends(get_session)]
RedisDep = Annotated[Redis, Depends(get_redis)]
TaskQueueDep = Annotated[TaskQueue, Depends(get_task_queue)]


def get_event_publisher(redis: RedisDep) -> EventPublisher:
    return RedisEventPublisher(redis)


EventPublisherDep = Annotated[EventPublisher, Depends(get_event_publisher)]


def get_outbox(publisher: EventPublisherDep, task_queue: TaskQueueDep) -> Outbox:
    return Outbox(publisher, task_queue)


OutboxDep = Annotated[Outbox, Depends(get_outbox)]
