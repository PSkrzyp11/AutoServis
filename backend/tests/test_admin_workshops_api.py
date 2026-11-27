import uuid

import pytest
from fastapi import status
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import UserRole
from app.models.user import User
from app.models.workshop import Workshop
from tests.factories import (
    VALID_TAX_ID,
    assign_member,
    bearer,
    create_user,
    create_workshop,
    login,
)

ADMIN_WORKSHOPS_URL = "/api/v1/admin/workshops"
WORKSHOP_PAYLOAD = {
    "name": "Garaż pod Wawelem",
    "tax_id": VALID_TAX_ID,
    "street": "ul. Zakopiańska 62",
    "postal_code": "30-418",
    "city": "Kraków",
    "phone": "+48 12 345 67 89",
    "email": "Biuro@Example.com",
}


@pytest.fixture
async def admin_token(client: AsyncClient, db_session: AsyncSession) -> str:
    await create_user(db_session, email="admin@autoservis.pl", role=UserRole.ADMIN)
    return await login(client, "admin@autoservis.pl")


@pytest.fixture
async def workshop(db_session: AsyncSession) -> Workshop:
    return await create_workshop(db_session)


@pytest.fixture
async def mechanic(db_session: AsyncSession) -> User:
    return await create_user(db_session, email="mechanik@example.com", role=UserRole.MECHANIC)


def members_url(workshop: Workshop) -> str:
    return f"{ADMIN_WORKSHOPS_URL}/{workshop.id}/members"


async def test_admin_creates_workshop_with_unique_slug(
    client: AsyncClient,
    admin_token: str,
) -> None:
    first = await client.post(
        ADMIN_WORKSHOPS_URL, headers=bearer(admin_token), json=WORKSHOP_PAYLOAD
    )
    second = await client.post(
        ADMIN_WORKSHOPS_URL, headers=bearer(admin_token), json=WORKSHOP_PAYLOAD
    )

    assert first.status_code == status.HTTP_201_CREATED
    assert first.json()["slug"] == "garaz-pod-wawelem"
    assert first.json()["email"] == "biuro@example.com"
    assert first.json()["timezone"] == "Europe/Warsaw"
    assert second.json()["slug"] == "garaz-pod-wawelem-2"


async def test_create_workshop_validates_tax_id(client: AsyncClient, admin_token: str) -> None:
    response = await client.post(
        ADMIN_WORKSHOPS_URL,
        headers=bearer(admin_token),
        json={**WORKSHOP_PAYLOAD, "tax_id": "5252389142"},
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    fields = [item["field"] for item in response.json()["error"]["details"]["fields"]]
    assert fields == ["tax_id"]


async def test_non_admin_cannot_create_workshop(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    await create_user(db_session, email="kierownik@example.com", role=UserRole.MANAGER)
    manager_token = await login(client, "kierownik@example.com")

    response = await client.post(
        ADMIN_WORKSHOPS_URL,
        headers=bearer(manager_token),
        json=WORKSHOP_PAYLOAD,
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN


async def test_admin_lists_and_deactivates_workshops(
    client: AsyncClient,
    workshop: Workshop,
    admin_token: str,
) -> None:
    deactivated = await client.patch(
        f"{ADMIN_WORKSHOPS_URL}/{workshop.id}",
        headers=bearer(admin_token),
        json={"is_active": False},
    )
    inactive_list = await client.get(
        ADMIN_WORKSHOPS_URL,
        headers=bearer(admin_token),
        params={"is_active": "false"},
    )
    public_list = await client.get("/api/v1/workshops")
    missing = await client.patch(
        f"{ADMIN_WORKSHOPS_URL}/{uuid.uuid4()}",
        headers=bearer(admin_token),
        json={"is_active": True},
    )

    assert deactivated.json()["is_active"] is False
    assert [item["id"] for item in inactive_list.json()["items"]] == [str(workshop.id)]
    assert public_list.json()["total"] == 0
    assert missing.status_code == status.HTTP_404_NOT_FOUND


async def test_admin_assigns_and_removes_members(
    client: AsyncClient,
    workshop: Workshop,
    mechanic: User,
    admin_token: str,
) -> None:
    url = members_url(workshop)

    added = await client.post(url, headers=bearer(admin_token), json={"user_id": str(mechanic.id)})
    duplicate = await client.post(
        url,
        headers=bearer(admin_token),
        json={"user_id": str(mechanic.id)},
    )
    removed = await client.delete(f"{url}/{mechanic.id}", headers=bearer(admin_token))
    removed_again = await client.delete(f"{url}/{mechanic.id}", headers=bearer(admin_token))

    assert added.status_code == status.HTTP_201_CREATED
    assert added.json()["role"] == "MECHANIC"
    assert duplicate.json()["error"]["code"] == "MEMBER_ALREADY_EXISTS"
    assert removed.status_code == status.HTTP_204_NO_CONTENT
    assert removed_again.status_code == status.HTTP_404_NOT_FOUND


async def test_only_staff_can_be_assigned(
    client: AsyncClient,
    db_session: AsyncSession,
    workshop: Workshop,
    admin_token: str,
) -> None:
    regular_client = await create_user(db_session, email="klient@example.com")

    not_staff = await client.post(
        members_url(workshop),
        headers=bearer(admin_token),
        json={"user_id": str(regular_client.id)},
    )
    unknown_user = await client.post(
        members_url(workshop),
        headers=bearer(admin_token),
        json={"user_id": str(uuid.uuid4())},
    )

    assert not_staff.json()["error"]["code"] == "USER_NOT_STAFF"
    assert unknown_user.status_code == status.HTTP_404_NOT_FOUND


async def test_changing_role_to_client_removes_workshop_access(
    client: AsyncClient,
    db_session: AsyncSession,
    workshop: Workshop,
    mechanic: User,
    admin_token: str,
) -> None:
    await assign_member(db_session, workshop, mechanic)

    await client.patch(
        f"/api/v1/admin/users/{mechanic.id}",
        headers=bearer(admin_token),
        json={"role": "CLIENT"},
    )
    await client.patch(
        f"/api/v1/admin/users/{mechanic.id}",
        headers=bearer(admin_token),
        json={"role": "MECHANIC"},
    )
    mechanic_token = await login(client, mechanic.email)
    response = await client.get(
        f"/api/v1/workshops/{workshop.id}",
        headers=bearer(mechanic_token),
    )

    assert response.json()["error"]["code"] == "WORKSHOP_ACCESS_DENIED"
