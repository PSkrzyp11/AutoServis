from urllib.parse import parse_qs, urlparse

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
from tests.fakes import FakeTaskQueue

REQUEST_URL = "/api/v1/auth/password-reset/request"
CONFIRM_URL = "/api/v1/auth/password-reset/confirm"
REFRESH_URL = "/api/v1/auth/refresh"
NEW_PASSWORD = "Nowe-haslo-456"
USER_EMAIL = "jan.kowalski@example.com"


def extract_token(reset_url: str) -> str:
    return parse_qs(urlparse(reset_url).query)["token"][0]


async def request_reset_token(client: AsyncClient, task_queue: FakeTaskQueue) -> str:
    response = await client.post(REQUEST_URL, json={"email": USER_EMAIL})
    assert response.status_code == status.HTTP_202_ACCEPTED
    return extract_token(task_queue.password_reset_emails[-1].reset_url)


async def test_request_for_unknown_email_is_accepted_without_sending_email(
    client: AsyncClient,
    task_queue: FakeTaskQueue,
) -> None:
    response = await client.post(REQUEST_URL, json={"email": "nieznany@example.com"})

    assert response.status_code == status.HTTP_202_ACCEPTED
    assert task_queue.password_reset_emails == []


async def test_request_enqueues_email_with_reset_link(
    client: AsyncClient,
    db_session: AsyncSession,
    task_queue: FakeTaskQueue,
) -> None:
    await create_user(db_session, email=USER_EMAIL, full_name="Jan Kowalski")

    response = await client.post(REQUEST_URL, json={"email": USER_EMAIL})

    assert response.status_code == status.HTTP_202_ACCEPTED
    assert len(task_queue.password_reset_emails) == 1
    job = task_queue.password_reset_emails[0]
    assert job.recipient == USER_EMAIL
    assert job.full_name == "Jan Kowalski"
    assert job.reset_url.startswith("http://localhost:3000/nowe-haslo?token=")


async def test_request_for_inactive_account_does_not_send_email(
    client: AsyncClient,
    db_session: AsyncSession,
    task_queue: FakeTaskQueue,
) -> None:
    await create_user(db_session, email=USER_EMAIL, is_active=False)

    response = await client.post(REQUEST_URL, json={"email": USER_EMAIL})

    assert response.status_code == status.HTTP_202_ACCEPTED
    assert task_queue.password_reset_emails == []


async def test_confirm_sets_new_password_and_revokes_sessions(
    client: AsyncClient,
    db_session: AsyncSession,
    task_queue: FakeTaskQueue,
) -> None:
    await create_user(db_session, email=USER_EMAIL)
    await login(client, USER_EMAIL)
    previous_refresh_token = client.cookies.get("refresh_token")
    assert previous_refresh_token is not None
    reset_token = await request_reset_token(client, task_queue)

    confirm_response = await client.post(
        CONFIRM_URL,
        json={"token": reset_token, "new_password": NEW_PASSWORD},
    )
    old_password_response = await client.post(
        LOGIN_URL,
        json={"email": USER_EMAIL, "password": DEFAULT_PASSWORD},
    )
    new_password_response = await client.post(
        LOGIN_URL,
        json={"email": USER_EMAIL, "password": NEW_PASSWORD},
    )
    client.cookies.clear()
    old_session_response = await client.post(
        REFRESH_URL,
        headers=refresh_cookie_header(previous_refresh_token),
    )

    assert confirm_response.status_code == status.HTTP_204_NO_CONTENT
    assert old_password_response.status_code == status.HTTP_401_UNAUTHORIZED
    assert new_password_response.status_code == status.HTTP_200_OK
    assert old_session_response.status_code == status.HTTP_401_UNAUTHORIZED


async def test_confirm_with_invalid_token_fails(client: AsyncClient) -> None:
    response = await client.post(
        CONFIRM_URL,
        json={"token": "nieprawidlowy-token", "new_password": NEW_PASSWORD},
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["error"]["code"] == "INVALID_TOKEN"


async def test_reset_token_cannot_be_used_twice(
    client: AsyncClient,
    db_session: AsyncSession,
    task_queue: FakeTaskQueue,
) -> None:
    await create_user(db_session, email=USER_EMAIL)
    reset_token = await request_reset_token(client, task_queue)
    payload = {"token": reset_token, "new_password": NEW_PASSWORD}

    first_response = await client.post(CONFIRM_URL, json=payload)
    second_response = await client.post(CONFIRM_URL, json=payload)

    assert first_response.status_code == status.HTTP_204_NO_CONTENT
    assert second_response.status_code == status.HTTP_400_BAD_REQUEST


async def test_new_request_invalidates_previous_token(
    client: AsyncClient,
    db_session: AsyncSession,
    task_queue: FakeTaskQueue,
) -> None:
    await create_user(db_session, email=USER_EMAIL)
    first_token = await request_reset_token(client, task_queue)
    second_token = await request_reset_token(client, task_queue)

    first_response = await client.post(
        CONFIRM_URL,
        json={"token": first_token, "new_password": NEW_PASSWORD},
    )
    second_response = await client.post(
        CONFIRM_URL,
        json={"token": second_token, "new_password": NEW_PASSWORD},
    )

    assert first_response.status_code == status.HTTP_400_BAD_REQUEST
    assert second_response.status_code == status.HTTP_204_NO_CONTENT
