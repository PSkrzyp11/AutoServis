import re
from decimal import Decimal
from typing import Annotated

from pydantic import AfterValidator, BeforeValidator, EmailStr, PlainSerializer, StringConstraints

from app.core.money import ALLOWED_VAT_RATES, round_money

PASSWORD_MIN_LENGTH = 8
PASSWORD_MAX_LENGTH = 128
FULL_NAME_MIN_LENGTH = 2
FULL_NAME_MAX_LENGTH = 200
PHONE_PATTERN = r"^\+?[0-9 ]{9,20}$"
POSTAL_CODE_PATTERN = r"^\d{2}-\d{3}$"
TAX_ID_WEIGHTS = (6, 5, 7, 2, 3, 4, 5, 6, 7)
TAX_ID_PATTERN = re.compile(r"^\d{10}$")
TAX_ID_MODULO = 11
TAX_ID_SEPARATORS = re.compile(r"[\s-]")


def normalize_email(email: str) -> str:
    return email.strip().lower()


def normalize_tax_id(value: object) -> object:
    return TAX_ID_SEPARATORS.sub("", value) if isinstance(value, str) else value


def validate_tax_id(value: str) -> str:
    if not TAX_ID_PATTERN.fullmatch(value):
        message = "Tax identification number must have 10 digits"
        raise ValueError(message)
    digits = [int(character) for character in value]
    weighted_digits = zip(TAX_ID_WEIGHTS, digits[: len(TAX_ID_WEIGHTS)], strict=True)
    checksum = sum(weight * digit for weight, digit in weighted_digits)
    if checksum % TAX_ID_MODULO != digits[-1]:
        message = "Tax identification number has an invalid checksum"
        raise ValueError(message)
    return value


def validate_vat_rate(value: Decimal) -> Decimal:
    if value not in ALLOWED_VAT_RATES:
        message = "VAT rate must be one of 0, 5, 8 or 23 percent"
        raise ValueError(message)
    return value


NormalizedEmail = Annotated[EmailStr, AfterValidator(normalize_email)]
Password = Annotated[
    str,
    StringConstraints(min_length=PASSWORD_MIN_LENGTH, max_length=PASSWORD_MAX_LENGTH),
]
FullName = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=FULL_NAME_MIN_LENGTH,
        max_length=FULL_NAME_MAX_LENGTH,
    ),
]
PhoneNumber = Annotated[str, StringConstraints(strip_whitespace=True, pattern=PHONE_PATTERN)]
PostalCode = Annotated[str, StringConstraints(strip_whitespace=True, pattern=POSTAL_CODE_PATTERN)]
TaxId = Annotated[str, BeforeValidator(normalize_tax_id), AfterValidator(validate_tax_id)]
VatRate = Annotated[Decimal, AfterValidator(validate_vat_rate)]


def serialize_decimal_amount(value: Decimal) -> str:
    return str(round_money(value))


DecimalAmount = Annotated[
    Decimal,
    PlainSerializer(serialize_decimal_amount, return_type=str, when_used="json"),
]
