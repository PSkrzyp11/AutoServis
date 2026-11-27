import uuid

import pytest
from fastapi import status
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import UserRole
from app.models.user import User
from tests.factories import bearer, create_user, login, refresh_cookie_header

ADMIN_USERS_URL = "/api/v1/admin/users"
REFRESH_URL = "/api/v1/auth/refresh"
ADMIN_EMAIL = "admin@autoservis.pl"


@pytest.fixture
async def admin(db_session: AsyncSession) -> User:
    return await create_user(
        db_session,
        email=ADMIN_EMAIL,
        full_name="Administrator Platformy",
        role=UserRole.ADMIN,
    )


@pytest.fixture
async def admin_token(client: AsyncClient, admin: User) -> str:
    return await login(client, admin.email)


async def create_clients(db_session: AsyncSession) -> list[User]:
    return [
        await create_user(db_session, email="anna.nowak@example.com", full_name="Anna Nowak"),
        await create_user(
            db_session,
            email="piotr.wisniewski@example.com",
            full_name="Piotr Wiśniewski",
            role=UserRole.MECHANIC,
        ),
        await create_user(
            db_session,
            email="ewa.zielinska@example.com",
            full_name="Ewa Zielińska",
            is_active=False,
        ),
    ]


async def test_client_cannot_list_users(client: AsyncClient, db_session: AsyncSession) -> None:
    await create_user(db_session, email="jan.kowalski@example.com")
    access_token = await login(client, "jan.kowalski@example.com")

    response = await client.get(ADMIN_USERS_URL, headers=bearer(access_token))

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json()["error"]["code"] == "FORBIDDEN"


async def test_admin_lists_users_with_pagination(
    client: AsyncClient,
    db_session: AsyncSession,
    admin_token: str,
) -> None:
    await create_clients(db_session)

    response = await client.get(
        ADMIN_USERS_URL,
        headers=bearer(admin_token),
        params={"limit": 2, "offset": 0},
    )

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["total"] == 4
    assert body["limit"] == 2
    assert body["offset"] == 0
    assert len(body["items"]) == 2


async def test_admin_filters_users_by_role_status_and_search(
    client: AsyncClient,
    db_session: AsyncSession,
    admin_token: str,
) -> None:
    await create_clients(db_session)

    by_role = await client.get(
        ADMIN_USERS_URL,
        headers=bearer(admin_token),
        params={"role": "MECHANIC"},
    )
    by_status = await client.get(
        ADMIN_USERS_URL,
        headers=bearer(admin_token),
        params={"is_active": "false"},
    )
    by_search = await client.get(
        ADMIN_USERS_URL,
        headers=bearer(admin_token),
        params={"search": "NOWAK"},
    )

    assert [user["email"] for user in by_role.json()["items"]] == ["piotr.wisniewski@example.com"]
    assert [user["email"] for user in by_status.json()["items"]] == ["ewa.zielinska@example.com"]
    assert [user["email"] for user in by_search.json()["items"]] == ["anna.nowak@example.com"]


async def test_admin_search_treats_wildcards_literally(
    client: AsyncClient,
    db_session: AsyncSession,
    admin_token: str,
) -> None:
    await create_clients(db_session)

    response = await client.get(
        ADMIN_USERS_URL,
        headers=bearer(admin_token),
        params={"search": "%"},
    )

    assert response.json()["total"] == 0


async def test_admin_sorts_users_by_email_ascending(
    client: AsyncClient,
    db_session: AsyncSession,
    admin_token: str,
) -> None:
    await create_clients(db_session)

    response = await client.get(
        ADMIN_USERS_URL,
        headers=bearer(admin_token),
        params={"sort_by": "email", "sort_order": "asc"},
    )

    emails = [user["email"] for user in response.json()["items"]]
    assert emails == sorted(emails)


async def test_admin_changes_user_role(
    client: AsyncClient,
    db_session: AsyncSession,
    admin_token: str,
) -> None:
    user = await create_user(db_session, email="jan.kowalski@example.com")

    response = await client.patch(
        f"{ADMIN_USERS_URL}/{user.id}",
        headers=bearer(admin_token),
        json={"role": "MANAGER"},
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["role"] == "MANAGER"


async def test_admin_deactivation_revokes_user_sessions(
    client: AsyncClient,
    db_session: AsyncSession,
    admin: User,
) -> None:
    user = await create_user(db_session, email="jan.kowalski@example.com")
    await login(client, user.email)
    user_refresh_token = client.cookies.get("refresh_token")
    assert user_refresh_token is not None
    admin_token = await login(client, admin.email)

    deactivate_response = await client.patch(
        f"{ADMIN_USERS_URL}/{user.id}",
        headers=bearer(admin_token),
        json={"is_active": False},
    )
    client.cookies.clear()
    refresh_response = await client.post(
        REFRESH_URL,
        headers=refresh_cookie_header(user_refresh_token),
    )

    assert deactivate_response.status_code == status.HTTP_200_OK
    assert deactivate_response.json()["is_active"] is False
    assert refresh_response.status_code == status.HTTP_401_UNAUTHORIZED


async def test_admin_cannot_modify_own_account(
    client: AsyncClient,
    admin: User,
    admin_token: str,
) -> None:
    response = await client.patch(
        f"{ADMIN_USERS_URL}/{admin.id}",
        headers=bearer(admin_token),
        json={"role": "CLIENT"},
    )

    assert response.status_code == status.HTTP_409_CONFLICT
    assert response.json()["error"]["code"] == "SELF_MODIFICATION_FORBIDDEN"


async def test_admin_gets_single_user(
    client: AsyncClient,
    db_session: AsyncSession,
    admin_token: str,
) -> None:
    user = await create_user(db_session, email="jan.kowalski@example.com")

    response = await client.get(f"{ADMIN_USERS_URL}/{user.id}", headers=bearer(admin_token))

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["id"] == str(user.id)


async def test_unknown_user_returns_not_found(client: AsyncClient, admin_token: str) -> None:
    response = await client.get(f"{ADMIN_USERS_URL}/{uuid.uuid4()}", headers=bearer(admin_token))

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["error"]["code"] == "NOT_FOUND"


async def test_invalid_user_id_returns_validation_error(
    client: AsyncClient,
    admin_token: str,
) -> None:
    response = await client.get(f"{ADMIN_USERS_URL}/nie-uuid", headers=bearer(admin_token))

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    fields = [item["field"] for item in response.json()["error"]["details"]["fields"]]
    assert fields == ["user_id"]
