import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.vehicle import Vehicle
from app.repositories.query_helpers import fetch_page
from app.schemas.pagination import PageParams


class VehicleRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_for_owner(
        self,
        owner_id: uuid.UUID,
        page: PageParams,
    ) -> tuple[Sequence[Vehicle], int]:
        return await fetch_page(
            self._session,
            select(Vehicle),
            [Vehicle.owner_id == owner_id, Vehicle.deleted_at.is_(None)],
            [Vehicle.created_at.desc(), Vehicle.id.asc()],
            page,
        )

    async def get_for_owner(self, owner_id: uuid.UUID, vehicle_id: uuid.UUID) -> Vehicle | None:
        result = await self._session.execute(
            select(Vehicle).where(
                Vehicle.id == vehicle_id,
                Vehicle.owner_id == owner_id,
                Vehicle.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def find_active_by_owner_and_plate(
        self,
        owner_id: uuid.UUID,
        plate_number: str,
    ) -> Vehicle | None:
        result = await self._session.execute(
            select(Vehicle).where(
                Vehicle.owner_id == owner_id,
                Vehicle.plate_number == plate_number,
                Vehicle.deleted_at.is_(None),
            )
        )
        return result.scalars().first()

    async def vin_taken(self, vin: str, *, excluded_id: uuid.UUID | None = None) -> bool:
        query = select(Vehicle.id).where(Vehicle.vin == vin, Vehicle.deleted_at.is_(None))
        if excluded_id is not None:
            query = query.where(Vehicle.id != excluded_id)
        return await self._session.scalar(query) is not None

    def add(self, vehicle: Vehicle) -> None:
        self._session.add(vehicle)
