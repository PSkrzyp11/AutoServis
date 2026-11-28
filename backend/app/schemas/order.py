import uuid
from datetime import datetime
from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from app.models.enums import OrderStatus
from app.models.service_order import DIAGNOSIS_MAX_LENGTH, STATUS_NOTE_MAX_LENGTH
from app.schemas.appointment import AppointmentVehicle, AppointmentWorkshop

DiagnosisText = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=DIAGNOSIS_MAX_LENGTH),
]
StatusNote = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=STATUS_NOTE_MAX_LENGTH),
]


class OrderScope(StrEnum):
    ACTIVE = "active"
    CLOSED = "closed"


class OrderSortField(StrEnum):
    NUMBER = "number"
    CREATED_AT = "created_at"
    STATUS_CHANGED_AT = "status_changed_at"


class OrderPerson(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    full_name: str


class OrderClient(OrderPerson):
    email: str
    phone: str | None


class OrderServiceType(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    duration_minutes: int


class OrderAppointment(BaseModel):
    id: uuid.UUID
    start_at: datetime
    end_at: datetime
    bay_name: str
    problem_description: str | None


class OrderHistoryEntry(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    from_status: OrderStatus | None = Field(
        description="Empty for the entry created with the order"
    )
    to_status: OrderStatus
    changed_at: datetime
    note: str | None
    changed_by: OrderPerson | None


class StaffOrderSummary(BaseModel):
    id: uuid.UUID
    number: int = Field(description="Sequential order number shown to people")
    status: OrderStatus
    status_changed_at: datetime
    created_at: datetime
    closed_at: datetime | None
    has_diagnosis: bool
    vehicle: AppointmentVehicle
    client: OrderClient
    service: OrderServiceType
    mechanic: OrderPerson | None
    appointment: OrderAppointment
    allowed_transitions: list[OrderStatus] = Field(
        description="Statuses the signed in user may move this order to right now"
    )


class StaffOrderDetail(StaffOrderSummary):
    diagnosis: str | None
    history: list[OrderHistoryEntry]


class OrderBoard(BaseModel):
    items: list[StaffOrderSummary]
    closed_since: datetime = Field(
        description="Completed and cancelled orders closed before this moment are left out"
    )


class ClientOrderHistoryEntry(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    from_status: OrderStatus | None
    to_status: OrderStatus
    changed_at: datetime


class ClientOrderRead(BaseModel):
    id: uuid.UUID
    number: int
    status: OrderStatus
    status_changed_at: datetime
    created_at: datetime
    closed_at: datetime | None
    workshop: AppointmentWorkshop
    vehicle: AppointmentVehicle
    service: OrderServiceType
    appointment_start_at: datetime
    mechanic: OrderPerson | None


class ClientOrderDetail(ClientOrderRead):
    diagnosis: str | None
    problem_description: str | None
    history: list[ClientOrderHistoryEntry]


class OrderStatusChange(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: OrderStatus = Field(description="Target status")
    expected_status: OrderStatus = Field(
        description="Status the client saw; a different current status returns a conflict"
    )
    note: StatusNote | None = Field(default=None, description="Optional note kept in the history")


class DiagnosisUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    diagnosis: DiagnosisText


class MechanicAssignment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mechanic_id: uuid.UUID | None = Field(
        description="Mechanic or manager of this workshop, or null to unassign"
    )
