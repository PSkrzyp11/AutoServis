import uuid
from typing import Annotated

from fastapi import APIRouter, Query, status

from app.api.dependencies import (
    AdminUserDep,
    ManagedWorkshopDep,
    PageParamsDep,
    WorkshopServiceDep,
)
from app.api.v1.workshop_mappers import to_member_read
from app.repositories.workshop_repository import WorkshopFilters
from app.schemas.errors import error_responses
from app.schemas.pagination import Page
from app.schemas.workshop import (
    AdminWorkshopUpdate,
    WorkshopCreate,
    WorkshopMemberCreate,
    WorkshopMemberRead,
    WorkshopRead,
)

FILTER_MAX_LENGTH = 100

router = APIRouter(prefix="/admin/workshops", tags=["admin"])

ADMIN_ERRORS = (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)


@router.get(
    "",
    summary="List all workshops",
    description="Includes inactive workshops. Available to administrators only.",
    responses=error_responses(*ADMIN_ERRORS),
)
async def list_workshops(
    *,
    _admin: AdminUserDep,
    workshop_service: WorkshopServiceDep,
    page: PageParamsDep,
    city: Annotated[str | None, Query(max_length=FILTER_MAX_LENGTH)] = None,
    search: Annotated[str | None, Query(max_length=FILTER_MAX_LENGTH)] = None,
    is_active: Annotated[bool | None, Query(description="Filter by status")] = None,
) -> Page[WorkshopRead]:
    workshops, total = await workshop_service.search(
        WorkshopFilters(city=city, search=search, is_active=is_active),
        page,
    )
    return Page[WorkshopRead](
        items=[WorkshopRead.model_validate(workshop) for workshop in workshops],
        total=total,
        limit=page.limit,
        offset=page.offset,
    )


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    summary="Create a workshop",
    description="The URL slug is generated from the name and never changes afterwards.",
    responses=error_responses(*ADMIN_ERRORS),
)
async def create_workshop(
    payload: WorkshopCreate,
    _admin: AdminUserDep,
    workshop_service: WorkshopServiceDep,
) -> WorkshopRead:
    return WorkshopRead.model_validate(await workshop_service.create(payload))


@router.patch(
    "/{workshop_id}",
    summary="Update or deactivate a workshop",
    responses=error_responses(*ADMIN_ERRORS, status.HTTP_404_NOT_FOUND),
)
async def update_workshop(
    payload: AdminWorkshopUpdate,
    _admin: AdminUserDep,
    workshop: ManagedWorkshopDep,
    workshop_service: WorkshopServiceDep,
) -> WorkshopRead:
    return WorkshopRead.model_validate(await workshop_service.update(workshop, payload))


@router.post(
    "/{workshop_id}/members",
    status_code=status.HTTP_201_CREATED,
    summary="Assign a mechanic or manager to a workshop",
    responses=error_responses(*ADMIN_ERRORS, status.HTTP_404_NOT_FOUND, status.HTTP_409_CONFLICT),
)
async def add_member(
    payload: WorkshopMemberCreate,
    _admin: AdminUserDep,
    workshop: ManagedWorkshopDep,
    workshop_service: WorkshopServiceDep,
) -> WorkshopMemberRead:
    return to_member_read(await workshop_service.add_member(workshop, payload.user_id))


@router.delete(
    "/{workshop_id}/members/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove a member from a workshop",
    responses=error_responses(*ADMIN_ERRORS, status.HTTP_404_NOT_FOUND),
)
async def remove_member(
    user_id: uuid.UUID,
    _admin: AdminUserDep,
    workshop: ManagedWorkshopDep,
    workshop_service: WorkshopServiceDep,
) -> None:
    await workshop_service.remove_member(workshop, user_id)
