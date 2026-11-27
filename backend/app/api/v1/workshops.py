from typing import Annotated

from fastapi import APIRouter, Query, status

from app.api.dependencies import (
    ManagedWorkshopDep,
    PageParamsDep,
    StaffWorkshopDep,
    WorkshopServiceDep,
)
from app.api.v1.workshop_mappers import to_member_read, to_public_detail, to_staff_detail
from app.repositories.workshop_repository import WorkshopFilters
from app.schemas.errors import error_responses
from app.schemas.pagination import Page
from app.schemas.workshop import (
    WorkshopMemberRead,
    WorkshopPublicDetail,
    WorkshopRead,
    WorkshopStaffDetail,
    WorkshopSummary,
    WorkshopUpdate,
)

FILTER_MAX_LENGTH = 100

router = APIRouter(prefix="/workshops", tags=["workshops"])

STAFF_ERROR_RESPONSES = error_responses(
    status.HTTP_401_UNAUTHORIZED,
    status.HTTP_403_FORBIDDEN,
    status.HTTP_404_NOT_FOUND,
)


@router.get(
    "",
    summary="Search active workshops",
    description="Public list of active workshops, optionally filtered by city and name.",
    responses=error_responses(),
)
async def search_workshops(
    workshop_service: WorkshopServiceDep,
    page: PageParamsDep,
    city: Annotated[
        str | None,
        Query(max_length=FILTER_MAX_LENGTH, description="Exact city name, case-insensitive"),
    ] = None,
    search: Annotated[
        str | None,
        Query(max_length=FILTER_MAX_LENGTH, description="Part of the workshop name"),
    ] = None,
) -> Page[WorkshopSummary]:
    workshops, total = await workshop_service.search(
        WorkshopFilters(city=city, search=search, is_active=True),
        page,
    )
    return Page[WorkshopSummary](
        items=[WorkshopSummary.model_validate(workshop) for workshop in workshops],
        total=total,
        limit=page.limit,
        offset=page.offset,
    )


@router.get(
    "/cities",
    summary="List cities with active workshops",
    description="Distinct, alphabetically sorted cities, used by the search filter.",
)
async def list_cities(workshop_service: WorkshopServiceDep) -> list[str]:
    return list(await workshop_service.list_active_cities())


@router.get(
    "/slug/{slug}",
    summary="Get public workshop details",
    description="Contact data, weekly opening hours, upcoming closures and active services.",
    responses=error_responses(status.HTTP_404_NOT_FOUND),
)
async def get_workshop_by_slug(
    slug: str, workshop_service: WorkshopServiceDep
) -> WorkshopPublicDetail:
    return to_public_detail(await workshop_service.get_public_view(slug))


@router.get(
    "/{workshop_id}",
    summary="Get workshop details for staff",
    description="Available to administrators and to mechanics and managers of the workshop.",
    responses=STAFF_ERROR_RESPONSES,
)
async def get_workshop(
    workshop: StaffWorkshopDep,
    workshop_service: WorkshopServiceDep,
) -> WorkshopStaffDetail:
    return to_staff_detail(await workshop_service.get_staff_view(workshop))


@router.patch(
    "/{workshop_id}",
    summary="Update workshop contact data",
    description="Available to administrators and to managers of the workshop.",
    responses=STAFF_ERROR_RESPONSES,
)
async def update_workshop(
    payload: WorkshopUpdate,
    workshop: ManagedWorkshopDep,
    workshop_service: WorkshopServiceDep,
) -> WorkshopRead:
    return WorkshopRead.model_validate(await workshop_service.update(workshop, payload))


@router.get(
    "/{workshop_id}/members",
    summary="List workshop staff",
    responses=STAFF_ERROR_RESPONSES,
)
async def list_members(
    workshop: StaffWorkshopDep,
    workshop_service: WorkshopServiceDep,
) -> list[WorkshopMemberRead]:
    return [to_member_read(view) for view in await workshop_service.list_members(workshop)]
