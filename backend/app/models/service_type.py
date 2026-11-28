import uuid
from decimal import Decimal

from sqlalchemy import CheckConstraint, ForeignKey, Numeric, String, UniqueConstraint, true
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, string_enum
from app.models.enums import BayType

SERVICE_NAME_MAX_LENGTH = 150
MONEY_PRECISION = 12
MONEY_SCALE = 2
VAT_RATE_PRECISION = 5


class ServiceType(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "service_types"
    __table_args__ = (
        UniqueConstraint("workshop_id", "name"),
        CheckConstraint("duration_minutes > 0", name="duration_positive"),
        CheckConstraint("base_price_net >= 0", name="price_not_negative"),
        CheckConstraint("vat_rate >= 0 AND vat_rate <= 100", name="vat_rate_range"),
    )

    workshop_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workshops.id", ondelete="CASCADE"),
        index=True,
    )
    name: Mapped[str] = mapped_column(String(SERVICE_NAME_MAX_LENGTH))
    duration_minutes: Mapped[int]
    base_price_net: Mapped[Decimal] = mapped_column(Numeric(MONEY_PRECISION, MONEY_SCALE))
    vat_rate: Mapped[Decimal] = mapped_column(Numeric(VAT_RATE_PRECISION, MONEY_SCALE))
    required_bay_type: Mapped[BayType | None] = mapped_column(
        string_enum(BayType, "required_bay_type"),
    )
    is_active: Mapped[bool] = mapped_column(default=True, server_default=true())
