from datetime import timedelta

from fastapi import status
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.security import create_access_token
from app.core.time import utc_now
from tests.factories import bearer, create_user, login

ME_URL = "/api/v1/users/me"


async def test_me_requires_authentication(client: AsyncClient) -> None:
    response = await client.get(ME_URL)

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json()["error"]["code"] == "UNAUTHORIZED"
    assert response.headers["WWW-Authenticate"] == "Bearer"


async def test_me_rejects_malformed_token(client: AsyncClient) -> None:
    response = await client.get(ME_URL, headers=bearer("to-nie-jest-jwt"))

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json()["error"]["code"] == "INVALID_TOKEN"


async def test_me_rejects_expired_token(
    client: AsyncClient,
    db_session: AsyncSession,
    settings: Settings,
) -> None:
    user = await create_user(db_session)
    expired_token = create_access_token(user.id, settings, utc_now() - timedelta(hours=1))

    response = await client.get(ME_URL, headers=bearer(expired_token.value))

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json()["error"]["code"] == "TOKEN_EXPIRED"


async def test_me_returns_current_user(client: AsyncClient, db_session: AsyncSession) -> None:
    await create_user(db_session, email="jan.kowalski@example.com", full_name="Jan Kowalski")
    access_token = await login(client, "jan.kowalski@example.com")

    response = await client.get(ME_URL, headers=bearer(access_token))

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["email"] == "jan.kowalski@example.com"
    assert body["full_name"] == "Jan Kowalski"
    assert body["role"] == "CLIENT"


async def test_me_rejects_token_of_deactivated_user(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    user = await create_user(db_session, email="jan.kowalski@example.com")
    access_token = await login(client, "jan.kowalski@example.com")
    user.is_active = False
    await db_session.commit()

    response = await client.get(ME_URL, headers=bearer(access_token))

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json()["error"]["code"] == "USER_INACTIVE"


async def test_update_me_changes_profile_and_can_clear_phone(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    await create_user(db_session, email="jan.kowalski@example.com")
    access_token = await login(client, "jan.kowalski@example.com")

    update_response = await client.patch(
        ME_URL,
        headers=bearer(access_token),
        json={"full_name": "  Jan Nowak  ", "phone": "+48 501 202 303"},
    )
    clear_response = await client.patch(ME_URL, headers=bearer(access_token), json={"phone": None})

    assert update_response.status_code == status.HTTP_200_OK
    assert update_response.json()["full_name"] == "Jan Nowak"
    assert update_response.json()["phone"] == "+48 501 202 303"
    assert clear_response.json()["phone"] is None
    assert clear_response.json()["full_name"] == "Jan Nowak"


async def test_update_me_rejects_role_change(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    await create_user(db_session, email="jan.kowalski@example.com")
    access_token = await login(client, "jan.kowalski@example.com")

    response = await client.patch(ME_URL, headers=bearer(access_token), json={"role": "ADMIN"})

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
