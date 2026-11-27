import uuid

from sqlalchemy import ForeignKey, String, UniqueConstraint, true
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, string_enum
from app.models.enums import BayType

BAY_NAME_MAX_LENGTH = 100


class Bay(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "bays"
    __table_args__ = (UniqueConstraint("workshop_id", "name"),)

    workshop_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workshops.id", ondelete="CASCADE"),
        index=True,
    )
    name: Mapped[str] = mapped_column(String(BAY_NAME_MAX_LENGTH))
    type: Mapped[BayType] = mapped_column(string_enum(BayType, "bay_type"))
    is_active: Mapped[bool] = mapped_column(default=True, server_default=true())
