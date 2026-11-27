import uuid
from collections.abc import Sequence
from dataclasses import dataclass

from sqlalchemy import ColumnElement, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import InstrumentedAttribute

from app.models.enums import UserRole
from app.models.user import User
from app.repositories.query_helpers import LIKE_ESCAPE_CHARACTER, contains_pattern
from app.schemas.pagination import PageParams, SortOrder
from app.schemas.user import UserSortField

SORT_COLUMNS: dict[UserSortField, InstrumentedAttribute[object]] = {
    UserSortField.CREATED_AT: User.created_at,
    UserSortField.EMAIL: User.email,
    UserSortField.FULL_NAME: User.full_name,
}


@dataclass(frozen=True)
class UserFilters:
    role: UserRole | None = None
    is_active: bool | None = None
    search: str | None = None


@dataclass(frozen=True)
class UserSorting:
    field: UserSortField = UserSortField.CREATED_AT
    order: SortOrder = SortOrder.DESC


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, user_id: uuid.UUID) -> User | None:
        return await self._session.get(User, user_id)

    async def get_by_email(self, email: str) -> User | None:
        result = await self._session.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    def add(self, user: User) -> None:
        self._session.add(user)

    async def search(
        self,
        filters: UserFilters,
        sorting: UserSorting,
        page: PageParams,
    ) -> tuple[Sequence[User], int]:
        conditions = self._build_conditions(filters)
        total = await self._session.scalar(
            select(func.count()).select_from(User).where(*conditions)
        )
        query = (
            select(User)
            .where(*conditions)
            .order_by(self._order_clause(sorting), User.id)
            .limit(page.limit)
            .offset(page.offset)
        )
        result = await self._session.execute(query)
        return result.scalars().all(), total or 0

    @staticmethod
    def _build_conditions(filters: UserFilters) -> list[ColumnElement[bool]]:
        conditions: list[ColumnElement[bool]] = []
        if filters.role is not None:
            conditions.append(User.role == filters.role)
        if filters.is_active is not None:
            conditions.append(User.is_active.is_(filters.is_active))
        if filters.search:
            pattern = contains_pattern(filters.search)
            conditions.append(
                or_(
                    User.email.ilike(pattern, escape=LIKE_ESCAPE_CHARACTER),
                    User.full_name.ilike(pattern, escape=LIKE_ESCAPE_CHARACTER),
                )
            )
        return conditions

    @staticmethod
    def _order_clause(sorting: UserSorting) -> ColumnElement[object]:
        column = SORT_COLUMNS[sorting.field]
        return column.asc() if sorting.order is SortOrder.ASC else column.desc()
