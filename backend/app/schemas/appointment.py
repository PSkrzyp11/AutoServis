import uuid
from datetime import date, datetime
from enum import StrEnum
from typing import Annotated

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, StringConstraints

from app.models.appointment import PROBLEM_DESCRIPTION_MAX_LENGTH
from app.models.enums import AppointmentStatus, OrderStatus, UserRole
from app.schemas.service_type import ServiceTypeRead

ProblemDescription = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        max_length=PROBLEM_DESCRIPTION_MAX_LENGTH,
    ),
]


class AppointmentScope(StrEnum):
    UPCOMING = "upcoming"
    PAST = "past"


class AvailableSlotRead(BaseModel):
    start_at: datetime = Field(description="Slot start in UTC")
    end_at: datetime = Field(description="Slot end in UTC")


class DayAvailability(BaseModel):
    day: date = Field(description="Local date in the workshop time zone")
    service_type_id: uuid.UUID
    duration_minutes: int
    slots: list[AvailableSlotRead]


class AppointmentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    workshop_id: uuid.UUID
    service_type_id: uuid.UUID
    vehicle_id: uuid.UUID = Field(description="One of the vehicles owned by the signed in user")
    start_at: AwareDatetime = Field(
        description="Start of a slot returned by the availability endpoint"
    )
    problem_description: ProblemDescription | None = Field(
        default=None,
        description="Symptoms or wishes described by the client",
    )


class AppointmentWorkshop(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    slug: str
    name: str
    street: str
    postal_code: str
    city: str
    phone: str


class AppointmentVehicle(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    make: str
    model: str
    production_year: int
    plate_number: str


class AppointmentBay(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str


class AppointmentClient(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    full_name: str
    email: str
    phone: str | None
    role: UserRole


class AppointmentOrder(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    number: int
    status: OrderStatus


class AppointmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    status: AppointmentStatus
    start_at: datetime
    end_at: datetime
    problem_description: str | None
    created_at: datetime
    cancelled_at: datetime | None
    workshop: AppointmentWorkshop
    service_type: ServiceTypeRead
    vehicle: AppointmentVehicle
    bay: AppointmentBay
    order: AppointmentOrder | None = Field(description="Service order opened at check-in")


class StaffAppointmentRead(AppointmentRead):
    client: AppointmentClient
