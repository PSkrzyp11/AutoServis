import uuid
from datetime import date, datetime, time
from typing import Annotated

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

from app.models.enums import IsoWeekday, UserRole
from app.schemas.bay import BayRead
from app.schemas.common import NormalizedEmail, PhoneNumber, PostalCode, TaxId
from app.schemas.service_type import ServiceTypeRead

WorkshopName = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=3, max_length=200)
]
Street = Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=200)]
City = Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=100)]
ClosureReason = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)
]


class WorkshopCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: WorkshopName = Field(description="Public name of the workshop")
    tax_id: TaxId = Field(description="Polish tax identification number (NIP), 10 digits")
    street: Street = Field(description="Street and building number")
    postal_code: PostalCode = Field(description="Postal code in the 00-000 format")
    city: City
    phone: PhoneNumber
    email: NormalizedEmail


class WorkshopUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: WorkshopName | None = None
    tax_id: TaxId | None = None
    street: Street | None = None
    postal_code: PostalCode | None = None
    city: City | None = None
    phone: PhoneNumber | None = None
    email: NormalizedEmail | None = None


class AdminWorkshopUpdate(WorkshopUpdate):
    is_active: bool | None = Field(default=None, description="Whether the workshop is listed")


class WorkshopSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    slug: str
    name: str
    street: str
    postal_code: str
    city: str
    phone: str


class WorkshopRead(WorkshopSummary):
    tax_id: str
    email: str
    timezone: str
    is_active: bool
    created_at: datetime


class OpeningHoursEntry(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    weekday: IsoWeekday = Field(description="ISO weekday, 1 is Monday and 7 is Sunday")
    opens_at: time = Field(description="Local opening time in the workshop time zone")
    closes_at: time = Field(description="Local closing time in the workshop time zone")

    @model_validator(mode="after")
    def validate_time_range(self) -> "OpeningHoursEntry":
        if self.closes_at <= self.opens_at:
            message = "Closing time must be later than opening time"
            raise ValueError(message)
        return self


class OpeningHoursUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    days: list[OpeningHoursEntry] = Field(
        max_length=len(IsoWeekday),
        description="Weekly schedule, days that are not listed are closed",
    )

    @field_validator("days")
    @classmethod
    def validate_unique_weekdays(cls, days: list[OpeningHoursEntry]) -> list[OpeningHoursEntry]:
        weekdays = [day.weekday for day in days]
        if len(weekdays) != len(set(weekdays)):
            message = "Each weekday can appear only once"
            raise ValueError(message)
        return sorted(days, key=lambda day: day.weekday)


class ClosureCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    closed_on: date = Field(description="Local date when the workshop is closed")
    reason: ClosureReason | None = None


class ClosureRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    closed_on: date
    reason: str | None


class WorkshopPublicDetail(WorkshopSummary):
    email: str
    opening_hours: list[OpeningHoursEntry]
    upcoming_closures: list[ClosureRead]
    service_types: list[ServiceTypeRead]


class WorkshopStaffDetail(WorkshopRead):
    opening_hours: list[OpeningHoursEntry]
    bays: list[BayRead]


class WorkshopMemberCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_id: uuid.UUID = Field(description="Mechanic or manager to assign to the workshop")


class WorkshopMemberRead(BaseModel):
    user_id: uuid.UUID
    full_name: str
    email: str
    phone: str | None
    role: UserRole
    joined_at: datetime
