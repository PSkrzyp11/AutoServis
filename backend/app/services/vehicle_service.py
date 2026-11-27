import uuid
from collections.abc import Sequence

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ConflictError, ErrorCode, NotFoundError
from app.core.logging import get_logger
from app.core.time import utc_now
from app.models.user import User
from app.models.vehicle import Vehicle
from app.repositories.vehicle_repository import VehicleRepository
from app.schemas.pagination import PageParams
from app.schemas.vehicle import VehicleCreate, VehicleUpdate
from app.services.updates import apply_changes

NULLABLE_VEHICLE_FIELDS = frozenset({"vin", "mileage_km", "engine"})

logger = get_logger()


def vin_taken_error() -> ConflictError:
    return ConflictError(
        ErrorCode.VIN_ALREADY_REGISTERED,
        "A vehicle with this VIN is already registered",
    )


class VehicleService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._vehicles = VehicleRepository(session)

    async def list_vehicles(
        self,
        owner: User,
        page: PageParams,
    ) -> tuple[Sequence[Vehicle], int]:
        return await self._vehicles.list_for_owner(owner.id, page)

    async def get_vehicle(self, owner: User, vehicle_id: uuid.UUID) -> Vehicle:
        vehicle = await self._vehicles.get_for_owner(owner.id, vehicle_id)
        if vehicle is None:
            raise NotFoundError("Vehicle not found")
        return vehicle

    async def create(self, owner: User, data: VehicleCreate) -> Vehicle:
        if data.vin is not None and await self._vehicles.vin_taken(data.vin):
            raise vin_taken_error()
        vehicle = Vehicle(
            owner_id=owner.id,
            make=data.make,
            model=data.model,
            production_year=data.production_year,
            plate_number=data.plate_number,
            vin=data.vin,
            mileage_km=data.mileage_km,
            engine=data.engine,
        )
        self._vehicles.add(vehicle)
        await self._commit_with_vin_guard()
        logger.info("vehicle_created", vehicle_id=str(vehicle.id))
        return vehicle

    async def update(self, owner: User, vehicle_id: uuid.UUID, data: VehicleUpdate) -> Vehicle:
        vehicle = await self.get_vehicle(owner, vehicle_id)
        if data.vin is not None and await self._vehicles.vin_taken(
            data.vin,
            excluded_id=vehicle.id,
        ):
            raise vin_taken_error()
        apply_changes(vehicle, data, nullable_fields=NULLABLE_VEHICLE_FIELDS)
        await self._commit_with_vin_guard()
        return vehicle

    async def delete(self, owner: User, vehicle_id: uuid.UUID) -> None:
        vehicle = await self.get_vehicle(owner, vehicle_id)
        vehicle.deleted_at = utc_now()
        await self._session.commit()
        logger.info("vehicle_deleted", vehicle_id=str(vehicle.id))

    async def _commit_with_vin_guard(self) -> None:
        try:
            await self._session.commit()
        except IntegrityError as error:
            await self._session.rollback()
            raise vin_taken_error() from error
