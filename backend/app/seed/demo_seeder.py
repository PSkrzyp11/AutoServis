from dataclasses import asdict, dataclass
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.core.money import PERCENT_DIVISOR, round_money
from app.core.security import hash_password
from app.core.text import slugify
from app.models.bay import Bay
from app.models.enums import UserRole
from app.models.service_type import ServiceType
from app.models.user import User
from app.models.vehicle import Vehicle
from app.models.workshop import Workshop, WorkshopClosure, WorkshopMember
from app.repositories.user_repository import UserRepository
from app.repositories.vehicle_repository import VehicleRepository
from app.repositories.workshop_repository import WorkshopRepository
from app.repositories.workshop_resource_repository import BayRepository, ServiceTypeRepository
from app.repositories.workshop_schedule_repository import WorkshopScheduleRepository
from app.schemas.service_type import ServiceTypeCreate
from app.schemas.vehicle import VehicleCreate
from app.schemas.workshop import OpeningHoursUpdate, WorkshopCreate
from app.seed.schemas import SeedData, SeedPerson, SeedWorkshop
from app.services.workshop_schedule_service import WorkshopScheduleService
from app.services.workshop_service import WorkshopService

logger = get_logger()


@dataclass
class SeedSummary:
    users_created: int = 0
    workshops_created: int = 0
    memberships_created: int = 0
    bays_created: int = 0
    service_types_created: int = 0
    closures_created: int = 0
    vehicles_created: int = 0


def adjusted_price(price: Decimal, adjustment_percent: int) -> Decimal:
    return round_money(price * (PERCENT_DIVISOR + adjustment_percent) / PERCENT_DIVISOR)


class DemoSeeder:
    def __init__(self, session: AsyncSession, password: str) -> None:
        self._session = session
        self._password_hash = hash_password(password)
        self._users = UserRepository(session)
        self._workshops = WorkshopRepository(session)
        self._schedule = WorkshopScheduleRepository(session)
        self._bays = BayRepository(session)
        self._service_types = ServiceTypeRepository(session)
        self._vehicles = VehicleRepository(session)
        self._workshop_service = WorkshopService(session)
        self._schedule_service = WorkshopScheduleService(session)
        self._summary = SeedSummary()

    async def run(self, data: SeedData) -> SeedSummary:
        for workshop_data in data.workshops:
            await self._seed_workshop(workshop_data, data.service_catalog)
        for client_data in data.clients:
            client = await self._ensure_user(client_data, UserRole.CLIENT)
            for vehicle_data in client_data.vehicles:
                await self._ensure_vehicle(client, vehicle_data)
        await self._session.commit()
        logger.info("demo_data_seeded", **asdict(self._summary))
        return self._summary

    async def _seed_workshop(
        self,
        data: SeedWorkshop,
        service_catalog: list[ServiceTypeCreate],
    ) -> None:
        workshop = await self._ensure_workshop(data)
        if not await self._schedule.list_opening_hours(workshop.id):
            await self._schedule_service.replace_opening_hours(
                workshop,
                OpeningHoursUpdate(days=data.opening_hours),
            )
        await self._ensure_closures(workshop, data)
        await self._ensure_bays(workshop, data)
        await self._ensure_service_types(workshop, service_catalog, data.price_adjustment_percent)
        for staff_data in data.staff:
            staff_member = await self._ensure_user(staff_data, staff_data.role)
            await self._ensure_membership(workshop, staff_member)

    async def _ensure_workshop(self, data: SeedWorkshop) -> Workshop:
        existing = await self._workshops.get_by_slug(slugify(data.name))
        if existing is not None:
            return existing
        self._summary.workshops_created += 1
        workshop_fields = data.model_dump(include=set(WorkshopCreate.model_fields))
        return await self._workshop_service.create(WorkshopCreate.model_validate(workshop_fields))

    async def _ensure_closures(self, workshop: Workshop, data: SeedWorkshop) -> None:
        for closure in data.closures:
            if await self._schedule.closure_exists(workshop.id, closure.closed_on):
                continue
            self._schedule.add_closure(
                WorkshopClosure(
                    workshop_id=workshop.id,
                    closed_on=closure.closed_on,
                    reason=closure.reason,
                )
            )
            self._summary.closures_created += 1

    async def _ensure_bays(self, workshop: Workshop, data: SeedWorkshop) -> None:
        for bay in data.bays:
            if await self._bays.name_taken(workshop.id, bay.name):
                continue
            self._bays.add(Bay(workshop_id=workshop.id, name=bay.name, type=bay.type))
            self._summary.bays_created += 1

    async def _ensure_service_types(
        self,
        workshop: Workshop,
        service_catalog: list[ServiceTypeCreate],
        price_adjustment_percent: int,
    ) -> None:
        for service in service_catalog:
            if await self._service_types.name_taken(workshop.id, service.name):
                continue
            self._service_types.add(
                ServiceType(
                    workshop_id=workshop.id,
                    name=service.name,
                    duration_minutes=service.duration_minutes,
                    base_price_net=adjusted_price(
                        service.base_price_net,
                        price_adjustment_percent,
                    ),
                    vat_rate=service.vat_rate,
                    required_bay_type=service.required_bay_type,
                )
            )
            self._summary.service_types_created += 1

    async def _ensure_user(self, data: SeedPerson, role: UserRole) -> User:
        existing = await self._users.get_by_email(data.email)
        if existing is not None:
            return existing
        user = User(
            email=data.email,
            full_name=data.full_name,
            phone=data.phone,
            role=role,
            password_hash=self._password_hash,
            is_active=True,
        )
        self._users.add(user)
        await self._session.flush()
        self._summary.users_created += 1
        return user

    async def _ensure_membership(self, workshop: Workshop, user: User) -> None:
        if await self._workshops.is_member(user.id, workshop.id):
            return
        self._workshops.add_member(WorkshopMember(user_id=user.id, workshop_id=workshop.id))
        await self._session.flush()
        self._summary.memberships_created += 1

    async def _ensure_vehicle(self, owner: User, data: VehicleCreate) -> None:
        if await self._vehicles.find_active_by_owner_and_plate(owner.id, data.plate_number):
            return
        if data.vin is not None and await self._vehicles.vin_taken(data.vin):
            return
        self._vehicles.add(
            Vehicle(
                owner_id=owner.id,
                make=data.make,
                model=data.model,
                production_year=data.production_year,
                plate_number=data.plate_number,
                vin=data.vin,
                mileage_km=data.mileage_km,
                engine=data.engine,
            )
        )
        await self._session.flush()
        self._summary.vehicles_created += 1
