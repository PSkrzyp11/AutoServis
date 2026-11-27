import uuid

import jwt
import pytest
from pydantic import SecretStr

from app.core.config import Settings
from app.core.errors import ErrorCode, UnauthorizedError
from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_opaque_token,
    hash_password,
    verify_password,
)
from app.core.time import utc_now


def test_password_hash_verifies_only_matching_password() -> None:
    password_hash = hash_password("Sekretne-haslo-123")

    assert password_hash != "Sekretne-haslo-123"
    assert verify_password("Sekretne-haslo-123", password_hash)
    assert not verify_password("Inne-haslo-123", password_hash)


def test_verify_password_returns_false_for_corrupted_hash() -> None:
    assert not verify_password("Sekretne-haslo-123", "not-an-argon2-hash")


def test_access_token_round_trip(settings: Settings) -> None:
    user_id = uuid.uuid4()

    token = create_access_token(user_id, settings, utc_now())

    assert decode_access_token(token.value, settings) == user_id
    assert token.expires_in_seconds == settings.access_token_ttl_minutes * 60


def test_access_token_signed_with_other_key_is_rejected(settings: Settings) -> None:
    forged_token = jwt.encode(
        {"sub": str(uuid.uuid4()), "type": "access", "iat": utc_now(), "exp": utc_now()},
        "another-secret-key-that-is-long-enough-to-sign",
        algorithm=settings.jwt_algorithm,
    )

    with pytest.raises(UnauthorizedError) as error:
        decode_access_token(forged_token, settings)

    assert error.value.code is ErrorCode.INVALID_TOKEN


def test_token_of_other_type_is_rejected(settings: Settings) -> None:
    now = utc_now()
    token = jwt.encode(
        {
            "sub": str(uuid.uuid4()),
            "type": "refresh",
            "iat": now,
            "exp": now + settings.access_token_ttl,
        },
        settings.jwt_secret_key.get_secret_value(),
        algorithm=settings.jwt_algorithm,
    )

    with pytest.raises(UnauthorizedError) as error:
        decode_access_token(token, settings)

    assert error.value.code is ErrorCode.INVALID_TOKEN


def test_token_with_non_uuid_subject_is_rejected(settings: Settings) -> None:
    now = utc_now()
    token = jwt.encode(
        {"sub": "admin", "type": "access", "iat": now, "exp": now + settings.access_token_ttl},
        settings.jwt_secret_key.get_secret_value(),
        algorithm=settings.jwt_algorithm,
    )

    with pytest.raises(UnauthorizedError) as error:
        decode_access_token(token, settings)

    assert error.value.code is ErrorCode.INVALID_TOKEN


def test_opaque_token_hash_is_deterministic_sha256() -> None:
    assert hash_opaque_token("abc") == hash_opaque_token("abc")
    assert len(hash_opaque_token("abc")) == 64
    assert hash_opaque_token("abc") != hash_opaque_token("abd")


def test_settings_reject_short_jwt_secret() -> None:
    with pytest.raises(ValueError, match="at least 32 characters"):
        Settings(
            database_url="postgresql+asyncpg://user:pass@localhost/db",
            redis_url="redis://localhost:6379/0",
            jwt_secret_key=SecretStr("too-short"),
        )
