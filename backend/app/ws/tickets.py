import hashlib
import secrets
import uuid
from dataclasses import dataclass

from pydantic import BaseModel, ValidationError
from redis.asyncio import Redis

TICKET_KEY_PREFIX = "realtime_ticket"
TICKET_BYTES = 32


class RealtimeGrant(BaseModel):
    user_id: uuid.UUID
    channels: tuple[str, ...]


@dataclass(frozen=True)
class IssuedTicket:
    ticket: str
    expires_in_seconds: int


def ticket_key(ticket: str) -> str:
    digest = hashlib.sha256(ticket.encode()).hexdigest()
    return f"{TICKET_KEY_PREFIX}:{digest}"


class RealtimeTicketStore:
    def __init__(self, redis: Redis, ttl_seconds: int) -> None:
        self._redis = redis
        self._ttl_seconds = ttl_seconds

    async def issue(self, grant: RealtimeGrant) -> IssuedTicket:
        ticket = secrets.token_urlsafe(TICKET_BYTES)
        await self._redis.set(ticket_key(ticket), grant.model_dump_json(), ex=self._ttl_seconds)
        return IssuedTicket(ticket=ticket, expires_in_seconds=self._ttl_seconds)

    async def consume(self, ticket: str) -> RealtimeGrant | None:
        stored = await self._redis.getdel(ticket_key(ticket))
        if stored is None:
            return None
        try:
            return RealtimeGrant.model_validate_json(stored)
        except ValidationError:
            return None
