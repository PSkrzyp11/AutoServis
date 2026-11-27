import uuid
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, computed_field

from app.core.money import gross_from_net
from app.schemas.common import DecimalAmount, VatRate

SLOT_MINUTES = 15
MAX_SERVICE_DURATION_MINUTES = 8 * 60
DEFAULT_VAT_RATE = Decimal(23)

ServiceName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=150)]
DurationMinutes = Annotated[
    int,
    Field(
        ge=SLOT_MINUTES,
        le=MAX_SERVICE_DURATION_MINUTES,
        multiple_of=SLOT_MINUTES,
        description="Booking duration, a multiple of 15 minutes",
    ),
]
NetPrice = Annotated[
    Decimal,
    Field(ge=0, max_digits=12, decimal_places=2, description="Base price net of VAT in PLN"),
]


class ServiceTypeCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: ServiceName
    duration_minutes: DurationMinutes
    base_price_net: NetPrice
    vat_rate: VatRate = Field(default=DEFAULT_VAT_RATE, description="VAT rate in percent")


class ServiceTypeUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: ServiceName | None = None
    duration_minutes: DurationMinutes | None = None
    base_price_net: NetPrice | None = None
    vat_rate: VatRate | None = None
    is_active: bool | None = None


class ServiceTypeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    duration_minutes: int
    base_price_net: DecimalAmount
    vat_rate: DecimalAmount
    is_active: bool

    @computed_field(description="Base price including VAT in PLN")
    def base_price_gross(self) -> DecimalAmount:
        return gross_from_net(self.base_price_net, self.vat_rate)
