from collections import defaultdict
from collections.abc import Iterable
from typing import Protocol

from starlette.websockets import WebSocketDisconnect

from app.core.logging import get_logger

logger = get_logger()


class RealtimeConnection(Protocol):
    async def send_text(self, data: str) -> None: ...


class ConnectionManager:
    def __init__(self) -> None:
        self._subscribers: defaultdict[str, set[RealtimeConnection]] = defaultdict(set)
        self._channels_by_connection: dict[RealtimeConnection, frozenset[str]] = {}

    def register(self, connection: RealtimeConnection, channels: Iterable[str]) -> None:
        subscribed = frozenset(channels)
        self._channels_by_connection[connection] = subscribed
        for channel in subscribed:
            self._subscribers[channel].add(connection)

    def unregister(self, connection: RealtimeConnection) -> None:
        for channel in self._channels_by_connection.pop(connection, frozenset()):
            subscribers = self._subscribers.get(channel)
            if subscribers is None:
                continue
            subscribers.discard(connection)
            if not subscribers:
                del self._subscribers[channel]

    def subscriber_count(self, channel: str) -> int:
        return len(self._subscribers.get(channel, ()))

    async def deliver(self, channel: str, message: str) -> None:
        for connection in tuple(self._subscribers.get(channel, ())):
            try:
                await connection.send_text(message)
            except (WebSocketDisconnect, RuntimeError, OSError):
                logger.info("realtime_connection_dropped", channel=channel)
                self.unregister(connection)
