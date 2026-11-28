from datetime import time
from pathlib import Path
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.enums import STAFF_ROLES, OrderStatus, UserRole
from app.schemas.bay import BayCreate
from app.schemas.common import FullName, NormalizedEmail, PhoneNumber
from app.schemas.order import DiagnosisText
from app.schemas.service_type import ServiceTypeCreate
from app.schemas.vehicle import PlateNumber, VehicleCreate
from app.schemas.workshop import ClosureCreate, OpeningHoursEntry, WorkshopCreate
from app.services.order_workflow import STATUSES_REQUIRING_DIAGNOSIS, path_to

DEMO_DATA_FILE = Path(__file__).resolve().parent / "data" / "pl" / "demo.json"
MAX_PRICE_ADJUSTMENT_PERCENT = 50
MAX_ORDER_AGE_DAYS = 30


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


class SeedOrder(BaseModel):
    model_config = ConfigDict(extra="forbid")

    workshop: str
    client_email: NormalizedEmail
    plate_number: PlateNumber
    service: str
    bay: str
    mechanic_email: NormalizedEmail | None
    days_ago: int = Field(ge=1, le=MAX_ORDER_AGE_DAYS)
    start_time: time
    status: OrderStatus
    diagnosis: DiagnosisText | None = None

    @model_validator(mode="after")
    def validate_diagnosis(self) -> Self:
        needs_diagnosis = any(
            status in STATUSES_REQUIRING_DIAGNOSIS for status in path_to(self.status)
        )
        if needs_diagnosis and self.diagnosis is None:
            message = f"Orders in status {self.status.value} need a diagnosis"
            raise ValueError(message)
        return self


class SeedData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    service_catalog: list[ServiceTypeCreate]
    workshops: list[SeedWorkshop]
    clients: list[SeedClient]
    orders: list[SeedOrder]


def load_seed_data(path: Path = DEMO_DATA_FILE) -> SeedData:
    return SeedData.model_validate_json(path.read_text(encoding="utf-8"))
