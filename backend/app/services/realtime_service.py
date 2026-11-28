from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import STAFF_ROLES
from app.models.user import User
from app.repositories.workshop_repository import WorkshopRepository
from app.ws.events import user_channel, workshop_channel
from app.ws.tickets import IssuedTicket, RealtimeGrant, RealtimeTicketStore


class RealtimeService:
    def __init__(self, session: AsyncSession, tickets: RealtimeTicketStore) -> None:
        self._workshops = WorkshopRepository(session)
        self._tickets = tickets

    async def issue_ticket(self, user: User) -> IssuedTicket:
        channels = [user_channel(user.id)]
        if user.role in STAFF_ROLES:
            workshops = await self._workshops.list_for_member(user.id)
            channels.extend(workshop_channel(workshop.id) for workshop in workshops)
        return await self._tickets.issue(RealtimeGrant(user_id=user.id, channels=tuple(channels)))
