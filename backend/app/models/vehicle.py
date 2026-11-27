import uuid

from sqlalchemy import CheckConstraint, ForeignKey, Index, SmallInteger, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin

VIN_LENGTH = 17
PLATE_NUMBER_MAX_LENGTH = 10
MAKE_MAX_LENGTH = 60
MODEL_MAX_LENGTH = 80
ENGINE_MAX_LENGTH = 60


class Vehicle(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "vehicles"
    __table_args__ = (
        CheckConstraint("mileage_km >= 0", name="mileage_not_negative"),
        Index(
            "uq_vehicles_vin_active",
            "vin",
            unique=True,
            postgresql_where=text("deleted_at IS NULL AND vin IS NOT NULL"),
        ),
    )

    owner_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )
    make: Mapped[str] = mapped_column(String(MAKE_MAX_LENGTH))
    model: Mapped[str] = mapped_column(String(MODEL_MAX_LENGTH))
    production_year: Mapped[int] = mapped_column(SmallInteger)
    plate_number: Mapped[str] = mapped_column(String(PLATE_NUMBER_MAX_LENGTH), index=True)
    vin: Mapped[str | None] = mapped_column(String(VIN_LENGTH))
    mileage_km: Mapped[int | None]
    engine: Mapped[str | None] = mapped_column(String(ENGINE_MAX_LENGTH))
