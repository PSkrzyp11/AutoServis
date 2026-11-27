from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import (
    PASSWORD_MAX_LENGTH,
    FullName,
    NormalizedEmail,
    Password,
    PhoneNumber,
)

RESET_TOKEN_MAX_LENGTH = 256


class RegisterRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: NormalizedEmail = Field(description="Email address used to sign in")
    password: Password = Field(description="Account password, at least 8 characters long")
    full_name: FullName = Field(description="First and last name of the account owner")
    phone: PhoneNumber | None = Field(default=None, description="Contact phone number")


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: NormalizedEmail = Field(description="Email address of the account")
    password: str = Field(min_length=1, max_length=PASSWORD_MAX_LENGTH)


class AccessTokenResponse(BaseModel):
    access_token: str = Field(description="Short-lived JWT sent as a Bearer token")
    token_type: Literal["bearer"] = "bearer"
    expires_in: int = Field(description="Access token lifetime in seconds")


class PasswordResetRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: NormalizedEmail = Field(description="Email address of the account to recover")


class PasswordResetConfirmRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    token: str = Field(
        min_length=1,
        max_length=RESET_TOKEN_MAX_LENGTH,
        description="Token received in the password reset email",
    )
    new_password: Password = Field(description="New account password")
