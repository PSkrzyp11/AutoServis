from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import STAFF_ROLES, UserRole
from app.schemas.bay import BayCreate
from app.schemas.common import FullName, NormalizedEmail, PhoneNumber
from app.schemas.service_type import ServiceTypeCreate
from app.schemas.vehicle import VehicleCreate
from app.schemas.workshop import ClosureCreate, OpeningHoursEntry, WorkshopCreate

DEMO_DATA_FILE = Path(__file__).resolve().parent / "data" / "pl" / "demo.json"
MAX_PRICE_ADJUSTMENT_PERCENT = 50


class SeedPerson(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: NormalizedEmail
    full_name: FullName
    phone: PhoneNumber


class SeedStaffMember(SeedPerson):
    role: UserRole

    @field_validator("role")
    @classmethod
    def validate_staff_role(cls, role: UserRole) -> UserRole:
        if role not in STAFF_ROLES:
            message = "Workshop staff must be a mechanic or a manager"
            raise ValueError(message)
        return role


class SeedClient(SeedPerson):
    vehicles: list[VehicleCreate]


class SeedWorkshop(WorkshopCreate):
    price_adjustment_percent: int = Field(
        ge=-MAX_PRICE_ADJUSTMENT_PERCENT,
        le=MAX_PRICE_ADJUSTMENT_PERCENT,
    )
    opening_hours: list[OpeningHoursEntry]
    closures: list[ClosureCreate]
    bays: list[BayCreate]
    staff: list[SeedStaffMember]


class SeedData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    service_catalog: list[ServiceTypeCreate]
    workshops: list[SeedWorkshop]
    clients: list[SeedClient]


def load_seed_data(path: Path = DEMO_DATA_FILE) -> SeedData:
    return SeedData.model_validate_json(path.read_text(encoding="utf-8"))
