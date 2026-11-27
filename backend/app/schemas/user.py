import uuid
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import UserRole
from app.schemas.common import FullName, PhoneNumber


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    full_name: str
    phone: str | None
    role: UserRole
    is_active: bool
    created_at: datetime


class UserProfileUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    full_name: FullName | None = Field(default=None, description="New full name")
    phone: PhoneNumber | None = Field(
        default=None,
        description="New phone number, send null to remove it",
    )


class AdminUserUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: UserRole | None = Field(default=None, description="New platform role")
    is_active: bool | None = Field(default=None, description="Whether the account can sign in")


class UserSortField(StrEnum):
    CREATED_AT = "created_at"
    EMAIL = "email"
    FULL_NAME = "full_name"
