import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, Computed, DateTime, ForeignKey, Index, Text, text
from sqlalchemy.dialects.postgresql import TSTZRANGE, ExcludeConstraint, Range
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, string_enum
from app.models.bay import Bay
from app.models.enums import AppointmentStatus
from app.models.service_type import ServiceType
from app.models.user import User
from app.models.vehicle import Vehicle
from app.models.workshop import Workshop

ACTIVE_STATUS_CONDITION = "status IN ('SCHEDULED', 'CHECKED_IN')"
PERIOD_EXPRESSION = "tstzrange(start_at, end_at, '[)')"
PROBLEM_DESCRIPTION_MAX_LENGTH = 2000


class Appointment(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "appointments"
    __table_args__ = (
        CheckConstraint("end_at > start_at", name="ends_after_start"),
        ExcludeConstraint(
            ("bay_id", "="),
            ("period", "&&"),
            using="gist",
            where=text(ACTIVE_STATUS_CONDITION),
            name="ex_appointments_bay_id_period",
        ),
        ExcludeConstraint(
            ("vehicle_id", "="),
            ("period", "&&"),
            using="gist",
            where=text(ACTIVE_STATUS_CONDITION),
            name="ex_appointments_vehicle_id_period",
        ),
        Index("ix_appointments_workshop_id_start_at", "workshop_id", "start_at"),
        Index("ix_appointments_status_start_at", "status", "start_at"),
    )

    workshop_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workshops.id", ondelete="CASCADE"))
    bay_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("bays.id", ondelete="RESTRICT"))
    vehicle_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("vehicles.id", ondelete="RESTRICT"))
    client_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )
    service_type_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("service_types.id", ondelete="RESTRICT"),
    )
    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    end_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    period: Mapped[Range[datetime]] = mapped_column(
        TSTZRANGE(),
        Computed(PERIOD_EXPRESSION, persisted=True),
    )
    status: Mapped[AppointmentStatus] = mapped_column(
        string_enum(AppointmentStatus, "appointment_status"),
        default=AppointmentStatus.SCHEDULED,
    )
    problem_description: Mapped[str | None] = mapped_column(Text())
    reminder_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    workshop: Mapped[Workshop] = relationship(lazy="raise")
    bay: Mapped[Bay] = relationship(lazy="raise")
    vehicle: Mapped[Vehicle] = relationship(lazy="raise")
    client: Mapped[User] = relationship(lazy="raise")
    service_type: Mapped[ServiceType] = relationship(lazy="raise")
