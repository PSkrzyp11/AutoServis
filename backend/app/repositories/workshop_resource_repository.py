import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.bay import Bay
from app.models.service_type import ServiceType


class BayRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_for_workshop(
        self,
        workshop_id: uuid.UUID,
        *,
        include_inactive: bool,
    ) -> Sequence[Bay]:
        query = select(Bay).where(Bay.workshop_id == workshop_id).order_by(Bay.name)
        if not include_inactive:
            query = query.where(Bay.is_active.is_(True))
        result = await self._session.execute(query)
        return result.scalars().all()

    async def get(self, workshop_id: uuid.UUID, bay_id: uuid.UUID) -> Bay | None:
        result = await self._session.execute(
            select(Bay).where(Bay.workshop_id == workshop_id, Bay.id == bay_id)
        )
        return result.scalar_one_or_none()

    async def name_taken(
        self,
        workshop_id: uuid.UUID,
        name: str,
        *,
        excluded_id: uuid.UUID | None = None,
    ) -> bool:
        query = select(Bay.id).where(Bay.workshop_id == workshop_id, Bay.name == name)
        if excluded_id is not None:
            query = query.where(Bay.id != excluded_id)
        return await self._session.scalar(query) is not None

    def add(self, bay: Bay) -> None:
        self._session.add(bay)


class ServiceTypeRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_for_workshop(
        self,
        workshop_id: uuid.UUID,
        *,
        include_inactive: bool,
    ) -> Sequence[ServiceType]:
        query = (
            select(ServiceType)
            .where(ServiceType.workshop_id == workshop_id)
            .order_by(ServiceType.name)
        )
        if not include_inactive:
            query = query.where(ServiceType.is_active.is_(True))
        result = await self._session.execute(query)
        return result.scalars().all()

    async def get(self, workshop_id: uuid.UUID, service_type_id: uuid.UUID) -> ServiceType | None:
        result = await self._session.execute(
            select(ServiceType).where(
                ServiceType.workshop_id == workshop_id,
                ServiceType.id == service_type_id,
            )
        )
        return result.scalar_one_or_none()

    async def name_taken(
        self,
        workshop_id: uuid.UUID,
        name: str,
        *,
        excluded_id: uuid.UUID | None = None,
    ) -> bool:
        query = select(ServiceType.id).where(
            ServiceType.workshop_id == workshop_id,
            ServiceType.name == name,
        )
        if excluded_id is not None:
            query = query.where(ServiceType.id != excluded_id)
        return await self._session.scalar(query) is not None

    def add(self, service_type: ServiceType) -> None:
        self._session.add(service_type)
