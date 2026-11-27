import uuid
from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ConflictError, ErrorCode, NotFoundError
from app.core.logging import get_logger
from app.models.bay import Bay
from app.models.service_type import ServiceType
from app.models.workshop import Workshop
from app.repositories.workshop_resource_repository import BayRepository, ServiceTypeRepository
from app.schemas.bay import BayCreate, BayUpdate
from app.schemas.service_type import ServiceTypeCreate, ServiceTypeUpdate
from app.services.updates import apply_changes

logger = get_logger()


def bay_name_taken_error() -> ConflictError:
    return ConflictError(ErrorCode.BAY_NAME_TAKEN, "A bay with this name already exists")


def service_name_taken_error() -> ConflictError:
    return ConflictError(ErrorCode.SERVICE_NAME_TAKEN, "A service with this name already exists")


class BayService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._bays = BayRepository(session)

    async def list_bays(self, workshop: Workshop, *, include_inactive: bool) -> Sequence[Bay]:
        return await self._bays.list_for_workshop(workshop.id, include_inactive=include_inactive)

    async def create(self, workshop: Workshop, data: BayCreate) -> Bay:
        if await self._bays.name_taken(workshop.id, data.name):
            raise bay_name_taken_error()
        bay = Bay(workshop_id=workshop.id, name=data.name, type=data.type, is_active=True)
        self._bays.add(bay)
        await self._session.commit()
        logger.info("bay_created", workshop_id=str(workshop.id), bay_id=str(bay.id))
        return bay

    async def update(self, workshop: Workshop, bay_id: uuid.UUID, data: BayUpdate) -> Bay:
        bay = await self._bays.get(workshop.id, bay_id)
        if bay is None:
            raise NotFoundError("Bay not found")
        if data.name is not None and await self._bays.name_taken(
            workshop.id,
            data.name,
            excluded_id=bay.id,
        ):
            raise bay_name_taken_error()
        apply_changes(bay, data)
        await self._session.commit()
        return bay


class ServiceTypeService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._service_types = ServiceTypeRepository(session)

    async def list_service_types(
        self,
        workshop: Workshop,
        *,
        include_inactive: bool,
    ) -> Sequence[ServiceType]:
        return await self._service_types.list_for_workshop(
            workshop.id,
            include_inactive=include_inactive,
        )

    async def create(self, workshop: Workshop, data: ServiceTypeCreate) -> ServiceType:
        if await self._service_types.name_taken(workshop.id, data.name):
            raise service_name_taken_error()
        service_type = ServiceType(
            workshop_id=workshop.id,
            name=data.name,
            duration_minutes=data.duration_minutes,
            base_price_net=data.base_price_net,
            vat_rate=data.vat_rate,
            is_active=True,
        )
        self._service_types.add(service_type)
        await self._session.commit()
        logger.info(
            "service_type_created",
            workshop_id=str(workshop.id),
            service_type_id=str(service_type.id),
        )
        return service_type

    async def update(
        self,
        workshop: Workshop,
        service_type_id: uuid.UUID,
        data: ServiceTypeUpdate,
    ) -> ServiceType:
        service_type = await self._service_types.get(workshop.id, service_type_id)
        if service_type is None:
            raise NotFoundError("Service not found")
        if data.name is not None and await self._service_types.name_taken(
            workshop.id,
            data.name,
            excluded_id=service_type.id,
        ):
            raise service_name_taken_error()
        apply_changes(service_type, data)
        await self._session.commit()
        return service_type
