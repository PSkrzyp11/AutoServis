from typing import Annotated

from pydantic import AfterValidator, EmailStr, StringConstraints

PASSWORD_MIN_LENGTH = 8
PASSWORD_MAX_LENGTH = 128
FULL_NAME_MIN_LENGTH = 2
FULL_NAME_MAX_LENGTH = 200
PHONE_PATTERN = r"^\+?[0-9 ]{9,20}$"


def normalize_email(email: str) -> str:
    return email.strip().lower()


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
