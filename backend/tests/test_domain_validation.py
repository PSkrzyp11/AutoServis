from datetime import time
from decimal import Decimal

import pytest
from pydantic import BaseModel, ValidationError

from app.core.money import gross_from_net
from app.core.text import slugify
from app.core.time import utc_now
from app.models.enums import IsoWeekday
from app.schemas.service_type import ServiceTypeCreate
from app.schemas.vehicle import VehicleCreate, VehicleUpdate
from app.schemas.workshop import OpeningHoursEntry, OpeningHoursUpdate, WorkshopCreate
from app.services.updates import apply_changes
from tests.factories import SECOND_VALID_TAX_ID, VALID_TAX_ID

VALID_WORKSHOP = {
    "name": "Auto Serwis Mokotów",
    "tax_id": VALID_TAX_ID,
    "street": "ul. Puławska 145",
    "postal_code": "02-715",
    "city": "Warszawa",
    "phone": "+48 22 123 45 67",
    "email": "kontakt@example.com",
}
VALID_VEHICLE = {
    "make": "Toyota",
    "model": "Corolla",
    "production_year": 2019,
    "plate_number": "WA 58213",
}


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("Garaż pod Wawelem", "garaz-pod-wawelem"),
        ("Auto-Serwis Łódź & Śródmieście", "auto-serwis-lodz-srodmiescie"),
        ("  Źródło Żółci  ", "zrodlo-zolci"),
        ("!!!", "item"),
    ],
)
def test_slugify_transliterates_polish_characters(name: str, expected: str) -> None:
    assert slugify(name) == expected


@pytest.mark.parametrize("tax_id", [VALID_TAX_ID, SECOND_VALID_TAX_ID, "525-238-91-41"])
def test_workshop_accepts_valid_tax_id(tax_id: str) -> None:
    workshop = WorkshopCreate.model_validate({**VALID_WORKSHOP, "tax_id": tax_id})

    assert workshop.tax_id.isdigit()
    assert len(workshop.tax_id) == 10


@pytest.mark.parametrize("tax_id", ["5252389142", "123", "ABCDEFGHIJ"])
def test_workshop_rejects_invalid_tax_id(tax_id: str) -> None:
    with pytest.raises(ValidationError):
        WorkshopCreate.model_validate({**VALID_WORKSHOP, "tax_id": tax_id})


def test_workshop_rejects_invalid_postal_code() -> None:
    with pytest.raises(ValidationError):
        WorkshopCreate.model_validate({**VALID_WORKSHOP, "postal_code": "02715"})


def test_vehicle_normalizes_plate_number_and_vin() -> None:
    vehicle = VehicleCreate.model_validate(
        {**VALID_VEHICLE, "plate_number": "wa 582-13", "vin": "sb1k93be10e412873"}
    )

    assert vehicle.plate_number == "WA58213"
    assert vehicle.vin == "SB1K93BE10E412873"


@pytest.mark.parametrize(
    "vin",
    ["SB1K93BE10E41287", "SB1K93BE10E4128731", "SB1K93BE10E41287O", "IB1K93BE10E412873"],
)
def test_vehicle_rejects_invalid_vin(vin: str) -> None:
    with pytest.raises(ValidationError):
        VehicleCreate.model_validate({**VALID_VEHICLE, "vin": vin})


@pytest.mark.parametrize("plate_number", ["W1", "1WA2345", "WA-123456789", "WA 12#45"])
def test_vehicle_rejects_invalid_plate_number(plate_number: str) -> None:
    with pytest.raises(ValidationError):
        VehicleCreate.model_validate({**VALID_VEHICLE, "plate_number": plate_number})


@pytest.mark.parametrize("production_year", [1899, utc_now().year + 2])
def test_vehicle_rejects_production_year_out_of_range(production_year: int) -> None:
    with pytest.raises(ValidationError):
        VehicleCreate.model_validate({**VALID_VEHICLE, "production_year": production_year})


def test_opening_hours_require_closing_after_opening() -> None:
    with pytest.raises(ValidationError):
        OpeningHoursEntry(weekday=IsoWeekday.MONDAY, opens_at=time(18), closes_at=time(8))


def test_opening_hours_reject_duplicate_weekdays_and_sort_days() -> None:
    with pytest.raises(ValidationError):
        OpeningHoursUpdate.model_validate(
            {
                "days": [
                    {"weekday": 1, "opens_at": "08:00", "closes_at": "16:00"},
                    {"weekday": 1, "opens_at": "09:00", "closes_at": "17:00"},
                ]
            }
        )

    schedule = OpeningHoursUpdate.model_validate(
        {
            "days": [
                {"weekday": 5, "opens_at": "08:00", "closes_at": "16:00"},
                {"weekday": 2, "opens_at": "08:00", "closes_at": "16:00"},
            ]
        }
    )
    assert [day.weekday for day in schedule.days] == [2, 5]


@pytest.mark.parametrize(
    ("payload", "is_valid"),
    [
        ({"duration_minutes": 45, "base_price_net": "149.99", "vat_rate": "23"}, True),
        ({"duration_minutes": 50, "base_price_net": "149.99", "vat_rate": "23"}, False),
        ({"duration_minutes": 45, "base_price_net": "149.999", "vat_rate": "23"}, False),
        ({"duration_minutes": 45, "base_price_net": "149.99", "vat_rate": "22"}, False),
        ({"duration_minutes": 45, "base_price_net": "-1", "vat_rate": "8"}, False),
    ],
)
def test_service_type_validation(payload: dict[str, object], *, is_valid: bool) -> None:
    data = {"name": "Diagnostyka komputerowa", **payload}
    if is_valid:
        ServiceTypeCreate.model_validate(data)
        return
    with pytest.raises(ValidationError):
        ServiceTypeCreate.model_validate(data)


@pytest.mark.parametrize(
    ("net", "vat_rate", "gross"),
    [
        ("100.00", "23", "123.00"),
        ("134.10", "23", "164.94"),
        ("0.05", "8", "0.05"),
        ("10", "0", "10.00"),
    ],
)
def test_gross_from_net_rounds_half_up(net: str, vat_rate: str, gross: str) -> None:
    assert gross_from_net(Decimal(net), Decimal(vat_rate)) == Decimal(gross)


class Target:
    def __init__(self) -> None:
        self.vin: str | None = "SB1K93BE10E412873"
        self.make = "Toyota"


def test_apply_changes_skips_unset_and_null_for_required_fields() -> None:
    target = Target()
    update = VehicleUpdate.model_validate({"vin": None, "make": None})

    applied = apply_changes(target, update, nullable_fields=frozenset({"vin"}))

    assert applied == {"vin": None}
    assert target.vin is None
    assert target.make == "Toyota"


def test_apply_changes_ignores_fields_not_sent() -> None:
    class EmptyUpdate(BaseModel):
        make: str | None = None

    target = Target()

    assert apply_changes(target, EmptyUpdate()) == {}
