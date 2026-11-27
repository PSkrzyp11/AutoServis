from fastapi import status
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.factories import (
    DEFAULT_PASSWORD,
    LOGIN_URL,
    create_user,
    login,
    refresh_cookie_header,
)

REGISTER_URL = "/api/v1/auth/register"
REFRESH_URL = "/api/v1/auth/refresh"
LOGOUT_URL = "/api/v1/auth/logout"
LOGIN_ATTEMPTS_LIMIT = 10


def current_refresh_token(client: AsyncClient) -> str:
    token = client.cookies.get("refresh_token")
    assert token is not None
    return token


async def test_register_creates_client_account(client: AsyncClient) -> None:
    response = await client.post(
        REGISTER_URL,
        json={
            "email": "Anna.Nowak@Example.com",
            "password": "Bezpieczne-haslo-1",
            "full_name": "Anna Nowak",
            "phone": "+48 600 100 200",
        },
    )

    assert response.status_code == status.HTTP_201_CREATED
    body = response.json()
    assert body["email"] == "anna.nowak@example.com"
    assert body["role"] == "CLIENT"
    assert body["is_active"] is True
    assert "password_hash" not in body


async def test_register_rejects_duplicate_email(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    await create_user(db_session, email="anna.nowak@example.com")

    response = await client.post(
        REGISTER_URL,
        json={
            "email": "anna.nowak@example.com",
            "password": "Bezpieczne-haslo-1",
            "full_name": "Anna Nowak",
        },
    )

    assert response.status_code == status.HTTP_409_CONFLICT
    assert response.json()["error"]["code"] == "EMAIL_ALREADY_REGISTERED"


async def test_register_returns_field_level_validation_errors(client: AsyncClient) -> None:
    response = await client.post(
        REGISTER_URL,
        json={"email": "not-an-email", "password": "short", "full_name": "A"},
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    error = response.json()["error"]
    assert error["code"] == "VALIDATION_ERROR"
    invalid_fields = {item["field"] for item in error["details"]["fields"]}
    assert {"email", "password", "full_name"} <= invalid_fields


async def test_register_does_not_accept_role_from_payload(client: AsyncClient) -> None:
    response = await client.post(
        REGISTER_URL,
        json={
            "email": "intruz@example.com",
            "password": "Bezpieczne-haslo-1",
            "full_name": "Intruz",
            "role": "ADMIN",
        },
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


async def test_login_returns_access_token_and_sets_session_cookies(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    await create_user(db_session, email="jan.kowalski@example.com")

    response = await client.post(
        LOGIN_URL,
        json={"email": "JAN.KOWALSKI@example.com", "password": DEFAULT_PASSWORD},
    )

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["expires_in"] == 15 * 60
    assert body["access_token"]

    cookies = response.headers.get_list("set-cookie")
    refresh_cookie = next(cookie for cookie in cookies if cookie.startswith("refresh_token="))
    assert "HttpOnly" in refresh_cookie
    assert "Path=/api/v1/auth" in refresh_cookie
    assert "samesite=lax" in refresh_cookie.lower()
    hint_cookie = next(cookie for cookie in cookies if cookie.startswith("session_present="))
    assert "HttpOnly" not in hint_cookie


async def test_login_with_wrong_password_is_rejected(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    await create_user(db_session, email="jan.kowalski@example.com")

    response = await client.post(
        LOGIN_URL,
        json={"email": "jan.kowalski@example.com", "password": "Zle-haslo-999"},
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json()["error"]["code"] == "INVALID_CREDENTIALS"


async def test_login_with_unknown_email_is_rejected(client: AsyncClient) -> None:
    response = await client.post(
        LOGIN_URL,
        json={"email": "nieznany@example.com", "password": DEFAULT_PASSWORD},
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json()["error"]["code"] == "INVALID_CREDENTIALS"


async def test_login_of_inactive_user_is_forbidden(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    await create_user(db_session, email="nieaktywny@example.com", is_active=False)

    response = await client.post(
        LOGIN_URL,
        json={"email": "nieaktywny@example.com", "password": DEFAULT_PASSWORD},
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json()["error"]["code"] == "USER_INACTIVE"


async def test_login_is_rate_limited(client: AsyncClient) -> None:
    credentials = {"email": "nieznany@example.com", "password": "Zle-haslo-999"}
    for _ in range(LOGIN_ATTEMPTS_LIMIT):
        response = await client.post(LOGIN_URL, json=credentials)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    response = await client.post(LOGIN_URL, json=credentials)

    assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
    assert response.json()["error"]["code"] == "RATE_LIMITED"
    assert int(response.headers["Retry-After"]) > 0


async def test_refresh_rotates_refresh_token(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    await create_user(db_session, email="jan.kowalski@example.com")
    await login(client, "jan.kowalski@example.com")
    initial_refresh_token = current_refresh_token(client)

    response = await client.post(REFRESH_URL)

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["access_token"]
    assert current_refresh_token(client) != initial_refresh_token


async def test_reusing_rotated_refresh_token_revokes_whole_session(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    await create_user(db_session, email="jan.kowalski@example.com")
    await login(client, "jan.kowalski@example.com")
    stolen_refresh_token = current_refresh_token(client)
    await client.post(REFRESH_URL)
    rotated_refresh_token = current_refresh_token(client)
    client.cookies.clear()

    reuse_response = await client.post(
        REFRESH_URL,
        headers=refresh_cookie_header(stolen_refresh_token),
    )
    client.cookies.clear()
    rotated_response = await client.post(
        REFRESH_URL,
        headers=refresh_cookie_header(rotated_refresh_token),
    )

    assert reuse_response.status_code == status.HTTP_401_UNAUTHORIZED
    assert reuse_response.json()["error"]["code"] == "INVALID_TOKEN"
    assert rotated_response.status_code == status.HTTP_401_UNAUTHORIZED


async def test_refresh_without_cookie_is_unauthorized_and_clears_cookies(
    client: AsyncClient,
) -> None:
    response = await client.post(REFRESH_URL)

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json()["error"]["code"] == "UNAUTHORIZED"
    cleared_cookies = response.headers.get_list("set-cookie")
    assert any(
        cookie.startswith('refresh_token=""') and "Max-Age=0" in cookie
        for cookie in cleared_cookies
    )


async def test_logout_revokes_refresh_token(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    await create_user(db_session, email="jan.kowalski@example.com")
    await login(client, "jan.kowalski@example.com")
    refresh_token = current_refresh_token(client)

    logout_response = await client.post(LOGOUT_URL)
    client.cookies.clear()
    refresh_response = await client.post(
        REFRESH_URL,
        headers=refresh_cookie_header(refresh_token),
    )

    assert logout_response.status_code == status.HTTP_204_NO_CONTENT
    assert refresh_response.status_code == status.HTTP_401_UNAUTHORIZED


async def test_logout_without_session_succeeds(client: AsyncClient) -> None:
    response = await client.post(LOGOUT_URL)

    assert response.status_code == status.HTTP_204_NO_CONTENT
