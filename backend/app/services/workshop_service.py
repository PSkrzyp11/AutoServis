import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum
from zoneinfo import ZoneInfo

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ConflictError, ErrorCode, ForbiddenError, NotFoundError
from app.core.logging import get_logger
from app.core.text import slugify
from app.core.time import utc_now
from app.models.bay import Bay
from app.models.enums import STAFF_ROLES, UserRole
from app.models.service_type import ServiceType
from app.models.user import User
from app.models.workshop import (
    WORKSHOP_SLUG_MAX_LENGTH,
    Workshop,
    WorkshopClosure,
    WorkshopMember,
    WorkshopOpeningHours,
)
from app.repositories.user_repository import UserRepository
from app.repositories.workshop_repository import WorkshopFilters, WorkshopRepository
from app.repositories.workshop_resource_repository import BayRepository, ServiceTypeRepository
from app.repositories.workshop_schedule_repository import WorkshopScheduleRepository
from app.schemas.pagination import PageParams
from app.schemas.workshop import WorkshopCreate, WorkshopUpdate
from app.services.updates import apply_changes

UPCOMING_CLOSURES_LIMIT = 10
FIRST_SLUG_SUFFIX = 2
SLUG_SUFFIX_RESERVE = 6

logger = get_logger()


class WorkshopPermission(StrEnum):
    VIEW = "view"
    MANAGE = "manage"


ROLES_WITH_PERMISSION: dict[WorkshopPermission, frozenset[UserRole]] = {
    WorkshopPermission.VIEW: STAFF_ROLES,
    WorkshopPermission.MANAGE: frozenset({UserRole.MANAGER}),
}


@dataclass(frozen=True)
class WorkshopPublicView:
    workshop: Workshop
    opening_hours: Sequence[WorkshopOpeningHours]
    upcoming_closures: Sequence[WorkshopClosure]
    service_types: Sequence[ServiceType]


@dataclass(frozen=True)
class WorkshopStaffView:
    workshop: Workshop
    opening_hours: Sequence[WorkshopOpeningHours]
    bays: Sequence[Bay]


@dataclass(frozen=True)
class WorkshopMemberView:
    user: User
    joined_at: datetime


def local_today(workshop: Workshop) -> date:
    return utc_now().astimezone(ZoneInfo(workshop.timezone)).date()


class WorkshopService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._workshops = WorkshopRepository(session)
        self._schedule = WorkshopScheduleRepository(session)
        self._bays = BayRepository(session)
        self._service_types = ServiceTypeRepository(session)
        self._users = UserRepository(session)

    async def get_workshop(self, workshop_id: uuid.UUID) -> Workshop:
        workshop = await self._workshops.get_by_id(workshop_id)
        if workshop is None:
            raise NotFoundError("Workshop not found")
        return workshop

    async def get_accessible_workshop(
        self,
        user: User,
        workshop_id: uuid.UUID,
        permission: WorkshopPermission,
    ) -> Workshop:
        workshop = await self.get_workshop(workshop_id)
        if user.role is UserRole.ADMIN:
            return workshop
        has_role = user.role in ROLES_WITH_PERMISSION[permission]
        if has_role and await self._workshops.is_member(user.id, workshop_id):
            return workshop
        raise ForbiddenError(
            ErrorCode.WORKSHOP_ACCESS_DENIED,
            "You do not have access to this workshop",
        )

    async def search(
        self,
        filters: WorkshopFilters,
        page: PageParams,
    ) -> tuple[Sequence[Workshop], int]:
        return await self._workshops.search(filters, page)

    async def list_active_cities(self) -> Sequence[str]:
        return await self._workshops.list_active_cities()

    async def get_public_view(self, slug: str) -> WorkshopPublicView:
        workshop = await self._workshops.get_by_slug(slug)
        if workshop is None or not workshop.is_active:
            raise NotFoundError("Workshop not found")
        return WorkshopPublicView(
            workshop=workshop,
            opening_hours=await self._schedule.list_opening_hours(workshop.id),
            upcoming_closures=await self._schedule.list_closures(
                workshop.id,
                from_date=local_today(workshop),
                limit=UPCOMING_CLOSURES_LIMIT,
            ),
            service_types=await self._service_types.list_for_workshop(
                workshop.id,
                include_inactive=False,
            ),
        )

    async def get_staff_view(self, workshop: Workshop) -> WorkshopStaffView:
        return WorkshopStaffView(
            workshop=workshop,
            opening_hours=await self._schedule.list_opening_hours(workshop.id),
            bays=await self._bays.list_for_workshop(workshop.id, include_inactive=True),
        )

    async def create(self, data: WorkshopCreate) -> Workshop:
        workshop = Workshop(
            name=data.name,
            slug=await self._unique_slug(data.name),
            tax_id=data.tax_id,
            street=data.street,
            postal_code=data.postal_code,
            city=data.city,
            phone=data.phone,
            email=data.email,
            is_active=True,
        )
        self._workshops.add(workshop)
        await self._session.commit()
        logger.info("workshop_created", workshop_id=str(workshop.id))
        return workshop

    async def update(self, workshop: Workshop, data: WorkshopUpdate) -> Workshop:
        changes = apply_changes(workshop, data)
        await self._session.commit()
        logger.info("workshop_updated", workshop_id=str(workshop.id), fields=sorted(changes))
        return workshop

    async def list_for_member(self, user: User) -> Sequence[Workshop]:
        return await self._workshops.list_for_member(user.id)

    async def list_members(self, workshop: Workshop) -> list[WorkshopMemberView]:
        rows = await self._workshops.list_members(workshop.id)
        return [WorkshopMemberView(user=user, joined_at=member.created_at) for user, member in rows]

    async def add_member(self, workshop: Workshop, user_id: uuid.UUID) -> WorkshopMemberView:
        user = await self._users.get_by_id(user_id)
        if user is None:
            raise NotFoundError("User not found")
        if user.role not in STAFF_ROLES:
            raise ConflictError(
                ErrorCode.USER_NOT_STAFF,
                "Only mechanics and managers can be assigned to a workshop",
            )
        if await self._workshops.is_member(user.id, workshop.id):
            raise ConflictError(
                ErrorCode.MEMBER_ALREADY_EXISTS,
                "User is already assigned to this workshop",
            )
        member = WorkshopMember(user_id=user.id, workshop_id=workshop.id)
        self._workshops.add_member(member)
        await self._session.commit()
        logger.info("workshop_member_added", workshop_id=str(workshop.id), user_id=str(user.id))
        return WorkshopMemberView(user=user, joined_at=member.created_at)

    async def remove_member(self, workshop: Workshop, user_id: uuid.UUID) -> None:
        if not await self._workshops.remove_member(user_id, workshop.id):
            raise NotFoundError("User is not assigned to this workshop")
        await self._session.commit()
        logger.info("workshop_member_removed", workshop_id=str(workshop.id), user_id=str(user_id))

    async def _unique_slug(self, name: str) -> str:
        base_slug = slugify(name)[: WORKSHOP_SLUG_MAX_LENGTH - SLUG_SUFFIX_RESERVE].strip("-")
        candidate = base_slug
        suffix = FIRST_SLUG_SUFFIX
        while await self._workshops.slug_exists(candidate):
            candidate = f"{base_slug}-{suffix}"
            suffix += 1
        return candidate
