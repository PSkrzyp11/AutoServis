from datetime import datetime

from sqlalchemy import DateTime, String, true
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, string_enum
from app.models.enums import UserRole

EMAIL_MAX_LENGTH = 320
FULL_NAME_MAX_LENGTH = 200
PHONE_MAX_LENGTH = 32


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(EMAIL_MAX_LENGTH), unique=True)
    password_hash: Mapped[str | None] = mapped_column(String(255))
    google_sub: Mapped[str | None] = mapped_column(String(255), unique=True)
    role: Mapped[UserRole] = mapped_column(
        string_enum(UserRole, "user_role"),
        default=UserRole.CLIENT,
    )
    full_name: Mapped[str] = mapped_column(String(FULL_NAME_MAX_LENGTH))
    phone: Mapped[str | None] = mapped_column(String(PHONE_MAX_LENGTH))
    is_active: Mapped[bool] = mapped_column(default=True, server_default=true())
    email_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
