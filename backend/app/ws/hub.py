import asyncio
import contextlib

from redis.asyncio import Redis
from redis.asyncio.client import PubSub
from redis.exceptions import RedisError

from app.core.logging import get_logger
from app.ws.events import CHANNEL_PATTERN
from app.ws.manager import ConnectionManager

PATTERN_MESSAGE_TYPE = "pmessage"
RECONNECT_DELAY_SECONDS = 1.0
MAX_RECONNECT_DELAY_SECONDS = 30.0
SUBSCRIBE_TIMEOUT_SECONDS = 5.0

logger = get_logger()


def as_text(value: str | bytes) -> str:
    return value.decode() if isinstance(value, bytes) else value


class RealtimeHub:
    def __init__(self, redis: Redis, manager: ConnectionManager) -> None:
        self._redis = redis
        self._manager = manager
        self._task: asyncio.Task[None] | None = None
        self._subscribed = asyncio.Event()

    async def start(self) -> None:
        self._task = asyncio.create_task(self._run(), name="realtime-hub")
        await asyncio.wait_for(self._subscribed.wait(), SUBSCRIBE_TIMEOUT_SECONDS)

    async def stop(self) -> None:
        if self._task is None:
            return
        self._task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await self._task
        self._task = None

    async def _run(self) -> None:
        delay = RECONNECT_DELAY_SECONDS
        while True:
            try:
                await self._listen()
            except RedisError:
                self._subscribed.clear()
                logger.warning("realtime_hub_disconnected", retry_in_seconds=delay)
                await asyncio.sleep(delay)
                delay = min(delay * 2, MAX_RECONNECT_DELAY_SECONDS)
            else:
                delay = RECONNECT_DELAY_SECONDS

    async def _listen(self) -> None:
        pubsub: PubSub
        async with self._redis.pubsub() as pubsub:
            await pubsub.psubscribe(CHANNEL_PATTERN)
            self._subscribed.set()
            logger.info("realtime_hub_subscribed", pattern=CHANNEL_PATTERN)
            async for message in pubsub.listen():
                if message["type"] != PATTERN_MESSAGE_TYPE:
                    continue
                await self._manager.deliver(as_text(message["channel"]), as_text(message["data"]))
