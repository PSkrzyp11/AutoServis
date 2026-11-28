from collections.abc import Collection
from enum import IntEnum
from typing import Protocol

from starlette.websockets import WebSocketDisconnect

from app.core.logging import get_logger
from app.ws.manager import ConnectionManager
from app.ws.tickets import RealtimeTicketStore

logger = get_logger()


class RealtimeCloseCode(IntEnum):
    INVALID_TICKET = 4401
    ORIGIN_NOT_ALLOWED = 4403


class RealtimeSocket(Protocol):
    async def accept(self) -> None: ...

    async def send_text(self, data: str) -> None: ...

    async def receive_text(self) -> str: ...

    async def close(self, code: int = ...) -> None: ...


class RealtimeGateway:
    def __init__(
        self,
        manager: ConnectionManager,
        tickets: RealtimeTicketStore,
        allowed_origins: Collection[str],
    ) -> None:
        self._manager = manager
        self._tickets = tickets
        self._allowed_origins = frozenset(allowed_origins)

    async def serve(self, socket: RealtimeSocket, ticket: str | None, origin: str | None) -> None:
        await socket.accept()
        if origin is not None and origin not in self._allowed_origins:
            logger.warning("realtime_origin_rejected", origin=origin)
            await socket.close(code=RealtimeCloseCode.ORIGIN_NOT_ALLOWED)
            return
        grant = await self._tickets.consume(ticket) if ticket else None
        if grant is None:
            await socket.close(code=RealtimeCloseCode.INVALID_TICKET)
            return

        self._manager.register(socket, grant.channels)
        logger.info("realtime_connected", user_id=str(grant.user_id), channels=len(grant.channels))
        try:
            while True:
                await socket.receive_text()
        except WebSocketDisconnect:
            logger.info("realtime_disconnected", user_id=str(grant.user_id))
        finally:
            self._manager.unregister(socket)
