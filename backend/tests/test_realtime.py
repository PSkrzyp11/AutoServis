import asyncio
import uuid
from collections.abc import Iterable
from dataclasses import dataclass, field

from fastapi import status
from httpx import AsyncClient
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.websockets import WebSocketDisconnect

from app.models.enums import UserRole
from app.ws.events import (
    RealtimeEvent,
    RealtimeEventType,
    RedisEventPublisher,
    user_channel,
    workshop_channel,
)
from app.ws.gateway import RealtimeCloseCode, RealtimeGateway
from app.ws.hub import RealtimeHub
from app.ws.manager import ConnectionManager, RealtimeConnection
from app.ws.tickets import RealtimeGrant, RealtimeTicketStore
from tests.factories import assign_member, bearer, create_user, create_workshop, login

TICKETS_URL = "/api/v1/realtime/tickets"
ALLOWED_ORIGIN = "http://localhost:3000"
DELIVERY_TIMEOUT_SECONDS = 5
UNREACHABLE_HOST = "127.0.0.1"
UNREACHABLE_PORT = 1


@dataclass
class FakeSocket:
    accepted: bool = False
    close_code: int | None = None
    sent: list[str] = field(default_factory=list)
    incoming: asyncio.Queue[str | None] = field(default_factory=asyncio.Queue)
    delivered: asyncio.Event = field(default_factory=asyncio.Event)

    async def accept(self) -> None:
        self.accepted = True

    async def send_text(self, data: str) -> None:
        self.sent.append(data)
        self.delivered.set()

    async def receive_text(self) -> str:
        message = await self.incoming.get()
        if message is None:
            raise WebSocketDisconnect
        return message

    async def close(self, code: int = 1000) -> None:
        self.close_code = code

    def __hash__(self) -> int:
        return id(self)

    def __eq__(self, other: object) -> bool:
        return self is other


class BrokenSocket(FakeSocket):
    async def send_text(self, data: str) -> None:
        raise RuntimeError(data)


class ObservedManager(ConnectionManager):
    def __init__(self) -> None:
        super().__init__()
        self.registered = asyncio.Event()

    def register(self, connection: RealtimeConnection, channels: Iterable[str]) -> None:
        super().register(connection, channels)
        self.registered.set()


def sample_event() -> RealtimeEvent:
    return RealtimeEvent(type=RealtimeEventType.ORDER_CHANGED, entity_id=uuid.uuid4())


async def test_tickets_carry_user_and_workshop_channels(
    client: AsyncClient,
    db_session: AsyncSession,
    redis: Redis,
) -> None:
    workshop = await create_workshop(db_session)
    mechanic = await create_user(db_session, email="marek@example.com", role=UserRole.MECHANIC)
    await assign_member(db_session, workshop, mechanic)
    customer = await create_user(db_session)
    store = RealtimeTicketStore(redis, ttl_seconds=30)

    staff_ticket = await client.post(
        TICKETS_URL, headers=bearer(await login(client, mechanic.email))
    )
    client_ticket = await client.post(
        TICKETS_URL, headers=bearer(await login(client, customer.email))
    )
    anonymous = await client.post(TICKETS_URL)

    assert staff_ticket.status_code == status.HTTP_201_CREATED
    assert staff_ticket.json()["expires_in_seconds"] == 30
    staff_grant = await store.consume(staff_ticket.json()["ticket"])
    client_grant = await store.consume(client_ticket.json()["ticket"])
    assert staff_grant is not None
    assert set(staff_grant.channels) == {
        user_channel(mechanic.id),
        workshop_channel(workshop.id),
    }
    assert client_grant is not None
    assert client_grant.channels == (user_channel(customer.id),)
    assert await store.consume(staff_ticket.json()["ticket"]) is None
    assert anonymous.status_code == status.HTTP_401_UNAUTHORIZED


async def test_gateway_rejects_foreign_origin_and_bad_tickets(redis: Redis) -> None:
    manager = ConnectionManager()
    store = RealtimeTicketStore(redis, ttl_seconds=30)
    gateway = RealtimeGateway(manager, store, [ALLOWED_ORIGIN])
    issued = await store.issue(RealtimeGrant(user_id=uuid.uuid4(), channels=("realtime:user:x",)))
    foreign, missing, unknown = FakeSocket(), FakeSocket(), FakeSocket()

    await gateway.serve(foreign, issued.ticket, "https://evil.example.com")
    await gateway.serve(missing, None, ALLOWED_ORIGIN)
    await gateway.serve(unknown, "not-a-ticket", ALLOWED_ORIGIN)

    assert foreign.close_code == RealtimeCloseCode.ORIGIN_NOT_ALLOWED
    assert missing.close_code == RealtimeCloseCode.INVALID_TICKET
    assert unknown.close_code == RealtimeCloseCode.INVALID_TICKET
    assert await store.consume(issued.ticket) is not None
    assert manager.subscriber_count("realtime:user:x") == 0


async def test_gateway_registers_connection_until_disconnect(redis: Redis) -> None:
    manager = ObservedManager()
    store = RealtimeTicketStore(redis, ttl_seconds=30)
    gateway = RealtimeGateway(manager, store, [ALLOWED_ORIGIN])
    channel = user_channel(uuid.uuid4())
    issued = await store.issue(RealtimeGrant(user_id=uuid.uuid4(), channels=(channel,)))
    socket = FakeSocket()

    serving = asyncio.create_task(gateway.serve(socket, issued.ticket, ALLOWED_ORIGIN))
    await asyncio.wait_for(manager.registered.wait(), DELIVERY_TIMEOUT_SECONDS)
    await socket.incoming.put("ping")
    await manager.deliver(channel, "hello")
    subscribed_while_open = manager.subscriber_count(channel)
    await socket.incoming.put(None)
    await serving

    assert socket.accepted
    assert socket.close_code is None
    assert socket.sent == ["hello"]
    assert subscribed_while_open == 1
    assert manager.subscriber_count(channel) == 0


async def test_manager_drops_broken_connections() -> None:
    manager = ConnectionManager()
    healthy, broken = FakeSocket(), BrokenSocket()
    manager.register(healthy, ["channel"])
    manager.register(broken, ["channel"])

    await manager.deliver("channel", "event")

    assert healthy.sent == ["event"]
    assert manager.subscriber_count("channel") == 1


async def test_hub_forwards_redis_messages_to_local_connections(redis: Redis) -> None:
    manager = ConnectionManager()
    hub = RealtimeHub(redis, manager)
    socket = FakeSocket()
    workshop_id = uuid.uuid4()
    channel = workshop_channel(workshop_id)
    manager.register(socket, [channel])
    event = RealtimeEvent(
        type=RealtimeEventType.ORDER_CHANGED,
        entity_id=uuid.uuid4(),
        workshop_id=workshop_id,
    )

    await hub.start()
    try:
        await RedisEventPublisher(redis).publish(channel, event)
        await RedisEventPublisher(redis).publish(workshop_channel(uuid.uuid4()), sample_event())
        await asyncio.wait_for(socket.delivered.wait(), DELIVERY_TIMEOUT_SECONDS)
    finally:
        await hub.stop()

    assert [RealtimeEvent.model_validate_json(item) for item in socket.sent] == [event]


async def test_publisher_survives_redis_errors() -> None:
    unreachable: Redis = Redis(host=UNREACHABLE_HOST, port=UNREACHABLE_PORT, socket_timeout=1)
    try:
        await RedisEventPublisher(unreachable).publish("realtime:user:x", sample_event())
    finally:
        await unreachable.aclose()
