import uuid
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from app.models.enums import BayType

BayName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]


class BayCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: BayName = Field(description="Name unique within the workshop, e.g. Lift A")
    type: BayType


class BayUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: BayName | None = None
    type: BayType | None = None
    is_active: bool | None = Field(default=None, description="Inactive bays cannot be booked")


class BayRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    type: BayType
    is_active: bool
