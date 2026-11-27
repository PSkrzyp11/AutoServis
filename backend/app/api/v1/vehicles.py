import uuid

from fastapi import APIRouter, status

from app.api.dependencies import CurrentUserDep, PageParamsDep, VehicleServiceDep
from app.schemas.errors import error_responses
from app.schemas.pagination import Page
from app.schemas.vehicle import VehicleCreate, VehicleRead, VehicleUpdate

router = APIRouter(prefix="/vehicles", tags=["vehicles"])

AUTH_ERRORS = (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)


@router.get(
    "",
    summary="List my vehicles",
    responses=error_responses(*AUTH_ERRORS),
)
async def list_vehicles(
    user: CurrentUserDep,
    vehicle_service: VehicleServiceDep,
    page: PageParamsDep,
) -> Page[VehicleRead]:
    vehicles, total = await vehicle_service.list_vehicles(user, page)
    return Page[VehicleRead](
        items=[VehicleRead.model_validate(vehicle) for vehicle in vehicles],
        total=total,
        limit=page.limit,
        offset=page.offset,
    )


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    summary="Add a vehicle",
    description="Plate numbers and VINs are normalized to upper case without spaces.",
    responses=error_responses(*AUTH_ERRORS, status.HTTP_409_CONFLICT),
)
async def create_vehicle(
    payload: VehicleCreate,
    user: CurrentUserDep,
    vehicle_service: VehicleServiceDep,
) -> VehicleRead:
    return VehicleRead.model_validate(await vehicle_service.create(user, payload))


@router.get(
    "/{vehicle_id}",
    summary="Get one of my vehicles",
    responses=error_responses(*AUTH_ERRORS, status.HTTP_404_NOT_FOUND),
)
async def get_vehicle(
    vehicle_id: uuid.UUID,
    user: CurrentUserDep,
    vehicle_service: VehicleServiceDep,
) -> VehicleRead:
    return VehicleRead.model_validate(await vehicle_service.get_vehicle(user, vehicle_id))


@router.patch(
    "/{vehicle_id}",
    summary="Update one of my vehicles",
    description="Send null for vin, mileage_km or engine to clear the value.",
    responses=error_responses(*AUTH_ERRORS, status.HTTP_404_NOT_FOUND, status.HTTP_409_CONFLICT),
)
async def update_vehicle(
    vehicle_id: uuid.UUID,
    payload: VehicleUpdate,
    user: CurrentUserDep,
    vehicle_service: VehicleServiceDep,
) -> VehicleRead:
    return VehicleRead.model_validate(await vehicle_service.update(user, vehicle_id, payload))


@router.delete(
    "/{vehicle_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove one of my vehicles",
    description="Vehicles are soft deleted so that service history stays intact.",
    responses=error_responses(*AUTH_ERRORS, status.HTTP_404_NOT_FOUND),
)
async def delete_vehicle(
    vehicle_id: uuid.UUID,
    user: CurrentUserDep,
    vehicle_service: VehicleServiceDep,
) -> None:
    await vehicle_service.delete(user, vehicle_id)
