import uuid
from datetime import date, time

from sqlalchemy import (
    CheckConstraint,
    Date,
    ForeignKey,
    SmallInteger,
    String,
    Time,
    UniqueConstraint,
    true,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, CreatedAtMixin, TimestampMixin, UUIDPrimaryKeyMixin

DEFAULT_WORKSHOP_TIMEZONE = "Europe/Warsaw"
WORKSHOP_NAME_MAX_LENGTH = 200
WORKSHOP_SLUG_MAX_LENGTH = 220
TAX_ID_LENGTH = 10
POSTAL_CODE_LENGTH = 6
CLOSURE_REASON_MAX_LENGTH = 200


class Workshop(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "workshops"

    name: Mapped[str] = mapped_column(String(WORKSHOP_NAME_MAX_LENGTH))
    slug: Mapped[str] = mapped_column(String(WORKSHOP_SLUG_MAX_LENGTH), unique=True)
    tax_id: Mapped[str] = mapped_column(String(TAX_ID_LENGTH))
    street: Mapped[str] = mapped_column(String(200))
    postal_code: Mapped[str] = mapped_column(String(POSTAL_CODE_LENGTH))
    city: Mapped[str] = mapped_column(String(100), index=True)
    phone: Mapped[str] = mapped_column(String(32))
    email: Mapped[str] = mapped_column(String(320))
    timezone: Mapped[str] = mapped_column(String(64), default=DEFAULT_WORKSHOP_TIMEZONE)
    is_active: Mapped[bool] = mapped_column(default=True, server_default=true())


class WorkshopMember(CreatedAtMixin, Base):
    __tablename__ = "workshop_members"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    workshop_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workshops.id", ondelete="CASCADE"),
        primary_key=True,
        index=True,
    )


class WorkshopOpeningHours(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "workshop_opening_hours"
    __table_args__ = (
        UniqueConstraint("workshop_id", "weekday"),
        CheckConstraint("weekday BETWEEN 1 AND 7", name="weekday_range"),
        CheckConstraint("closes_at > opens_at", name="closes_after_opens"),
    )

    workshop_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workshops.id", ondelete="CASCADE"),
    )
    weekday: Mapped[int] = mapped_column(SmallInteger)
    opens_at: Mapped[time] = mapped_column(Time())
    closes_at: Mapped[time] = mapped_column(Time())


class WorkshopClosure(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "workshop_closures"
    __table_args__ = (UniqueConstraint("workshop_id", "closed_on"),)

    workshop_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workshops.id", ondelete="CASCADE"),
    )
    closed_on: Mapped[date] = mapped_column(Date())
    reason: Mapped[str | None] = mapped_column(String(CLOSURE_REASON_MAX_LENGTH))
