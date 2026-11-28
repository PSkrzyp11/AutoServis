import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Identity, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.time import utc_now
from app.models.appointment import Appointment
from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, string_enum
from app.models.enums import OrderStatus
from app.models.user import User
from app.models.workshop import Workshop

DIAGNOSIS_MAX_LENGTH = 5000
STATUS_NOTE_MAX_LENGTH = 500


class ServiceOrder(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "service_orders"
    __table_args__ = (
        Index("ix_service_orders_workshop_id_status", "workshop_id", "status"),
        Index("ix_service_orders_mechanic_id", "mechanic_id"),
    )

    number: Mapped[int] = mapped_column(BigInteger, Identity(), unique=True)
    workshop_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workshops.id", ondelete="CASCADE"))
    appointment_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("appointments.id", ondelete="RESTRICT"),
        unique=True,
    )
    mechanic_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
    )
    status: Mapped[OrderStatus] = mapped_column(
        string_enum(OrderStatus, "order_status"),
        default=OrderStatus.RECEIVED,
    )
    diagnosis: Mapped[str | None] = mapped_column(Text())
    status_changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        server_default=func.now(),
    )
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    workshop: Mapped[Workshop] = relationship(lazy="raise")
    appointment: Mapped[Appointment] = relationship(back_populates="order", lazy="raise")
    mechanic: Mapped[User | None] = relationship(lazy="raise")
    history: Mapped[list["OrderStatusHistory"]] = relationship(
        back_populates="order",
        lazy="raise",
        order_by="OrderStatusHistory.changed_at",
        cascade="all, delete-orphan",
    )


class OrderStatusHistory(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "order_status_history"
    __table_args__ = (
        Index("ix_order_status_history_order_id_changed_at", "order_id", "changed_at"),
    )

    order_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("service_orders.id", ondelete="CASCADE"),
    )
    from_status: Mapped[OrderStatus | None] = mapped_column(
        string_enum(OrderStatus, "order_history_from_status"),
    )
    to_status: Mapped[OrderStatus] = mapped_column(
        string_enum(OrderStatus, "order_history_to_status"),
    )
    changed_by_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
    )
    note: Mapped[str | None] = mapped_column(String(STATUS_NOTE_MAX_LENGTH))
    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        server_default=func.now(),
    )

    order: Mapped[ServiceOrder] = relationship(back_populates="history", lazy="raise")
    changed_by: Mapped[User | None] = relationship(lazy="raise")
