import re
import uuid
from datetime import datetime
from typing import Annotated

from pydantic import (
    AfterValidator,
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    StringConstraints,
)

from app.core.time import utc_now

VIN_PATTERN = re.compile(r"^[A-HJ-NPR-Z0-9]{17}$")
PLATE_NUMBER_PATTERN = re.compile(r"^[A-Z]{1,3}[A-Z0-9]{2,5}$")
PLATE_NUMBER_MIN_LENGTH = 4
PLATE_NUMBER_MAX_LENGTH = 8
IDENTIFIER_SEPARATORS = re.compile(r"[\s-]")
EARLIEST_PRODUCTION_YEAR = 1900
MAX_MILEAGE_KM = 5_000_000


def normalize_identifier(value: object) -> object:
    return IDENTIFIER_SEPARATORS.sub("", value).upper() if isinstance(value, str) else value


def validate_vin(value: str) -> str:
    if not VIN_PATTERN.fullmatch(value):
        message = "VIN must have 17 characters without the letters I, O and Q"
        raise ValueError(message)
    return value


def validate_plate_number(value: str) -> str:
    is_valid_length = PLATE_NUMBER_MIN_LENGTH <= len(value) <= PLATE_NUMBER_MAX_LENGTH
    if not is_valid_length or not PLATE_NUMBER_PATTERN.fullmatch(value):
        message = "Plate number does not match the Polish registration format"
        raise ValueError(message)
    return value


def validate_production_year(value: int) -> int:
    latest_year = utc_now().year + 1
    if not EARLIEST_PRODUCTION_YEAR <= value <= latest_year:
        message = f"Production year must be between {EARLIEST_PRODUCTION_YEAR} and {latest_year}"
        raise ValueError(message)
    return value


Vin = Annotated[str, BeforeValidator(normalize_identifier), AfterValidator(validate_vin)]
PlateNumber = Annotated[
    str,
    BeforeValidator(normalize_identifier),
    AfterValidator(validate_plate_number),
]
ProductionYear = Annotated[int, AfterValidator(validate_production_year)]
Make = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=60)]
Model = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=80)]
Engine = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=60)]
MileageKm = Annotated[int, Field(ge=0, le=MAX_MILEAGE_KM, description="Odometer reading in km")]


class VehicleCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    make: Make = Field(description="Manufacturer, e.g. Toyota")
    model: Model = Field(description="Model name, e.g. Corolla")
    production_year: ProductionYear
    plate_number: PlateNumber = Field(description="Registration number, stored without spaces")
    vin: Vin | None = Field(default=None, description="Vehicle identification number")
    mileage_km: MileageKm | None = None
    engine: Engine | None = Field(default=None, description="Engine description, e.g. 1.6 TDI")


class VehicleUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    make: Make | None = None
    model: Model | None = None
    production_year: ProductionYear | None = None
    plate_number: PlateNumber | None = None
    vin: Vin | None = None
    mileage_km: MileageKm | None = None
    engine: Engine | None = None


class VehicleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    make: str
    model: str
    production_year: int
    plate_number: str
    vin: str | None
    mileage_km: int | None
    engine: str | None
    created_at: datetime
