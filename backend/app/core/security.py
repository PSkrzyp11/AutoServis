import hashlib
import secrets
import uuid
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from functools import cache

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

from app.core.config import Settings
from app.core.errors import ErrorCode, UnauthorizedError

OPAQUE_TOKEN_BYTES = 48
REQUIRED_ACCESS_TOKEN_CLAIMS = ["exp", "iat", "sub", "type"]
DUMMY_PASSWORD = "dummy-password-used-to-equalize-login-timing"

_password_hasher = PasswordHasher()


class TokenType(StrEnum):
    ACCESS = "access"


@dataclass(frozen=True)
class AccessToken:
    value: str
    expires_in_seconds: int


def hash_password(password: str) -> str:
    return _password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _password_hasher.verify(password_hash, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def password_needs_rehash(password_hash: str) -> bool:
    return _password_hasher.check_needs_rehash(password_hash)


@cache
def dummy_password_hash() -> str:
    return hash_password(DUMMY_PASSWORD)


def create_access_token(user_id: uuid.UUID, settings: Settings, now: datetime) -> AccessToken:
    expires_at = now + settings.access_token_ttl
    payload = {
        "sub": str(user_id),
        "type": TokenType.ACCESS.value,
        "iat": now,
        "exp": expires_at,
    }
    encoded = jwt.encode(
        payload,
        settings.jwt_secret_key.get_secret_value(),
        algorithm=settings.jwt_algorithm,
    )
    return AccessToken(
        value=encoded,
        expires_in_seconds=int(settings.access_token_ttl.total_seconds()),
    )


def decode_access_token(token: str, settings: Settings) -> uuid.UUID:
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key.get_secret_value(),
            algorithms=[settings.jwt_algorithm],
            options={"require": REQUIRED_ACCESS_TOKEN_CLAIMS},
        )
    except jwt.ExpiredSignatureError as error:
        raise UnauthorizedError(ErrorCode.TOKEN_EXPIRED, "Access token has expired") from error
    except jwt.InvalidTokenError as error:
        raise UnauthorizedError(ErrorCode.INVALID_TOKEN, "Access token is invalid") from error

    if payload.get("type") != TokenType.ACCESS.value:
        raise UnauthorizedError(ErrorCode.INVALID_TOKEN, "Access token is invalid")
    try:
        return uuid.UUID(str(payload["sub"]))
    except ValueError as error:
        raise UnauthorizedError(ErrorCode.INVALID_TOKEN, "Access token is invalid") from error


def generate_opaque_token() -> str:
    return secrets.token_urlsafe(OPAQUE_TOKEN_BYTES)


def hash_opaque_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
