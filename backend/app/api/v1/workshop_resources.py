import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Query, status

from app.api.dependencies import (
    BayServiceDep,
    ManagedWorkshopDep,
    ServiceTypeServiceDep,
    StaffWorkshopDep,
    WorkshopScheduleServiceDep,
)
from app.schemas.bay import BayCreate, BayRead, BayUpdate
from app.schemas.errors import error_responses
from app.schemas.service_type import ServiceTypeCreate, ServiceTypeRead, ServiceTypeUpdate
from app.schemas.workshop import ClosureCreate, ClosureRead, OpeningHoursEntry, OpeningHoursUpdate

router = APIRouter(prefix="/workshops/{workshop_id}", tags=["workshops"])

ACCESS_ERRORS = (
    status.HTTP_401_UNAUTHORIZED,
    status.HTTP_403_FORBIDDEN,
    status.HTTP_404_NOT_FOUND,
)
IncludeInactive = Annotated[
    bool,
    Query(description="Whether to include deactivated items"),
]


@router.put(
    "/opening-hours",
    summary="Replace the weekly opening hours",
    description="Days missing from the payload are treated as closed. Times are local.",
    responses=error_responses(*ACCESS_ERRORS),
)
async def replace_opening_hours(
    payload: OpeningHoursUpdate,
    workshop: ManagedWorkshopDep,
    schedule_service: WorkshopScheduleServiceDep,
) -> list[OpeningHoursEntry]:
    opening_hours = await schedule_service.replace_opening_hours(workshop, payload)
    return [OpeningHoursEntry.model_validate(day) for day in opening_hours]


@router.get(
    "/closures",
    summary="List closure days",
    responses=error_responses(*ACCESS_ERRORS),
)
async def list_closures(
    workshop: StaffWorkshopDep,
    schedule_service: WorkshopScheduleServiceDep,
    from_date: Annotated[
        date | None,
        Query(description="First date to include, defaults to today in the workshop time zone"),
    ] = None,
) -> list[ClosureRead]:
    closures = await schedule_service.list_closures(workshop, from_date)
    return [ClosureRead.model_validate(closure) for closure in closures]


@router.post(
    "/closures",
    status_code=status.HTTP_201_CREATED,
    summary="Add a closure day",
    responses=error_responses(*ACCESS_ERRORS, status.HTTP_409_CONFLICT),
)
async def add_closure(
    payload: ClosureCreate,
    workshop: ManagedWorkshopDep,
    schedule_service: WorkshopScheduleServiceDep,
) -> ClosureRead:
    return ClosureRead.model_validate(await schedule_service.add_closure(workshop, payload))


@router.delete(
    "/closures/{closure_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove a closure day",
    responses=error_responses(*ACCESS_ERRORS),
)
async def delete_closure(
    closure_id: uuid.UUID,
    workshop: ManagedWorkshopDep,
    schedule_service: WorkshopScheduleServiceDep,
) -> None:
    await schedule_service.delete_closure(workshop, closure_id)


@router.get(
    "/bays",
    summary="List service bays",
    responses=error_responses(*ACCESS_ERRORS),
)
async def list_bays(
    workshop: StaffWorkshopDep,
    bay_service: BayServiceDep,
    include_inactive: IncludeInactive = False,
) -> list[BayRead]:
    bays = await bay_service.list_bays(workshop, include_inactive=include_inactive)
    return [BayRead.model_validate(bay) for bay in bays]


@router.post(
    "/bays",
    status_code=status.HTTP_201_CREATED,
    summary="Create a service bay",
    responses=error_responses(*ACCESS_ERRORS, status.HTTP_409_CONFLICT),
)
async def create_bay(
    payload: BayCreate,
    workshop: ManagedWorkshopDep,
    bay_service: BayServiceDep,
) -> BayRead:
    return BayRead.model_validate(await bay_service.create(workshop, payload))


@router.patch(
    "/bays/{bay_id}",
    summary="Update or deactivate a service bay",
    responses=error_responses(*ACCESS_ERRORS, status.HTTP_409_CONFLICT),
)
async def update_bay(
    bay_id: uuid.UUID,
    payload: BayUpdate,
    workshop: ManagedWorkshopDep,
    bay_service: BayServiceDep,
) -> BayRead:
    return BayRead.model_validate(await bay_service.update(workshop, bay_id, payload))


@router.get(
    "/service-types",
    summary="List services offered by the workshop",
    responses=error_responses(*ACCESS_ERRORS),
)
async def list_service_types(
    workshop: StaffWorkshopDep,
    service_type_service: ServiceTypeServiceDep,
    include_inactive: IncludeInactive = False,
) -> list[ServiceTypeRead]:
    service_types = await service_type_service.list_service_types(
        workshop,
        include_inactive=include_inactive,
    )
    return [ServiceTypeRead.model_validate(item) for item in service_types]


@router.post(
    "/service-types",
    status_code=status.HTTP_201_CREATED,
    summary="Add a service to the workshop catalog",
    responses=error_responses(*ACCESS_ERRORS, status.HTTP_409_CONFLICT),
)
async def create_service_type(
    payload: ServiceTypeCreate,
    workshop: ManagedWorkshopDep,
    service_type_service: ServiceTypeServiceDep,
) -> ServiceTypeRead:
    return ServiceTypeRead.model_validate(await service_type_service.create(workshop, payload))


@router.patch(
    "/service-types/{service_type_id}",
    summary="Update or deactivate a service",
    responses=error_responses(*ACCESS_ERRORS, status.HTTP_409_CONFLICT),
)
async def update_service_type(
    service_type_id: uuid.UUID,
    payload: ServiceTypeUpdate,
    workshop: ManagedWorkshopDep,
    service_type_service: ServiceTypeServiceDep,
) -> ServiceTypeRead:
    service_type = await service_type_service.update(workshop, service_type_id, payload)
    return ServiceTypeRead.model_validate(service_type)
