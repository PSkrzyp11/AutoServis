import uuid
from collections.abc import Sequence
from dataclasses import dataclass

from sqlalchemy import ColumnElement, delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.workshop import Workshop, WorkshopMember
from app.repositories.query_helpers import LIKE_ESCAPE_CHARACTER, contains_pattern, fetch_page
from app.schemas.pagination import PageParams


@dataclass(frozen=True)
class WorkshopFilters:
    city: str | None = None
    search: str | None = None
    is_active: bool | None = None


class WorkshopRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, workshop_id: uuid.UUID) -> Workshop | None:
        return await self._session.get(Workshop, workshop_id)

    async def get_by_slug(self, slug: str) -> Workshop | None:
        result = await self._session.execute(select(Workshop).where(Workshop.slug == slug))
        return result.scalar_one_or_none()

    async def slug_exists(self, slug: str) -> bool:
        found = await self._session.scalar(select(Workshop.id).where(Workshop.slug == slug))
        return found is not None

    def add(self, workshop: Workshop) -> None:
        self._session.add(workshop)

    async def search(
        self,
        filters: WorkshopFilters,
        page: PageParams,
    ) -> tuple[Sequence[Workshop], int]:
        return await fetch_page(
            self._session,
            select(Workshop),
            self._build_conditions(filters),
            [Workshop.city.asc(), Workshop.name.asc(), Workshop.id.asc()],
            page,
        )

    async def list_active_cities(self) -> Sequence[str]:
        result = await self._session.execute(
            select(Workshop.city)
            .where(Workshop.is_active.is_(True))
            .distinct()
            .order_by(Workshop.city)
        )
        return result.scalars().all()

    async def list_for_member(self, user_id: uuid.UUID) -> Sequence[Workshop]:
        result = await self._session.execute(
            select(Workshop)
            .join(WorkshopMember, WorkshopMember.workshop_id == Workshop.id)
            .where(WorkshopMember.user_id == user_id)
            .order_by(Workshop.name)
        )
        return result.scalars().all()

    async def is_member(self, user_id: uuid.UUID, workshop_id: uuid.UUID) -> bool:
        member = await self._session.get(WorkshopMember, (user_id, workshop_id))
        return member is not None

    def add_member(self, member: WorkshopMember) -> None:
        self._session.add(member)

    async def remove_member(self, user_id: uuid.UUID, workshop_id: uuid.UUID) -> bool:
        result = await self._session.execute(
            delete(WorkshopMember)
            .where(WorkshopMember.user_id == user_id, WorkshopMember.workshop_id == workshop_id)
            .returning(WorkshopMember.user_id)
        )
        return result.scalar_one_or_none() is not None

    async def remove_all_memberships(self, user_id: uuid.UUID) -> None:
        await self._session.execute(delete(WorkshopMember).where(WorkshopMember.user_id == user_id))

    async def list_members(self, workshop_id: uuid.UUID) -> Sequence[tuple[User, WorkshopMember]]:
        result = await self._session.execute(
            select(User, WorkshopMember)
            .join(WorkshopMember, WorkshopMember.user_id == User.id)
            .where(WorkshopMember.workshop_id == workshop_id)
            .order_by(User.role, User.full_name)
        )
        return [(user, member) for user, member in result.all()]

    @staticmethod
    def _build_conditions(filters: WorkshopFilters) -> list[ColumnElement[bool]]:
        conditions: list[ColumnElement[bool]] = []
        if filters.is_active is not None:
            conditions.append(Workshop.is_active.is_(filters.is_active))
        if filters.city:
            conditions.append(func.lower(Workshop.city) == filters.city.strip().lower())
        if filters.search:
            conditions.append(
                Workshop.name.ilike(contains_pattern(filters.search), escape=LIKE_ESCAPE_CHARACTER)
            )
        return conditions
