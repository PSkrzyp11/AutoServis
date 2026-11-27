import uuid

import pytest
from fastapi import status
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import UserRole
from app.models.user import User
from app.models.workshop import Workshop
from tests.factories import assign_member, bearer, create_user, create_workshop, login

WORKSHOPS_URL = "/api/v1/workshops"


@pytest.fixture
async def workshop(db_session: AsyncSession) -> Workshop:
    return await create_workshop(db_session, name="Auto Serwis Mokotów", city="Warszawa")


@pytest.fixture
async def other_workshop(db_session: AsyncSession) -> Workshop:
    return await create_workshop(db_session, name="Garaż pod Wawelem", city="Kraków")


async def staff_token(
    client: AsyncClient,
    db_session: AsyncSession,
    workshop: Workshop,
    role: UserRole,
    email: str,
) -> str:
    user = await create_user(db_session, email=email, role=role)
    await assign_member(db_session, workshop, user)
    return await login(client, email)


@pytest.fixture
async def manager_token(client: AsyncClient, db_session: AsyncSession, workshop: Workshop) -> str:
    return await staff_token(
        client, db_session, workshop, UserRole.MANAGER, "kierownik@example.com"
    )


@pytest.fixture
async def mechanic_token(client: AsyncClient, db_session: AsyncSession, workshop: Workshop) -> str:
    return await staff_token(
        client, db_session, workshop, UserRole.MECHANIC, "mechanik@example.com"
    )


def resource_url(workshop: Workshop, resource: str = "") -> str:
    return f"{WORKSHOPS_URL}/{workshop.id}{resource}"


@pytest.mark.usefixtures("other_workshop")
async def test_public_search_filters_by_city_and_hides_inactive(
    client: AsyncClient,
    db_session: AsyncSession,
    workshop: Workshop,
) -> None:
    await create_workshop(db_session, name="Zamknięty Serwis", city="Kraków", is_active=False)

    all_active = await client.get(WORKSHOPS_URL)
    in_krakow = await client.get(WORKSHOPS_URL, params={"city": "KRAKÓW"})
    by_name = await client.get(WORKSHOPS_URL, params={"search": "mokot"})

    assert all_active.json()["total"] == 2
    assert [item["slug"] for item in in_krakow.json()["items"]] == ["garaz-pod-wawelem"]
    assert [item["id"] for item in by_name.json()["items"]] == [str(workshop.id)]


@pytest.mark.usefixtures("workshop", "other_workshop")
async def test_cities_lists_only_active_workshops(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    await create_workshop(db_session, name="Serwis Gdańsk", city="Gdańsk", is_active=False)

    response = await client.get(f"{WORKSHOPS_URL}/cities")

    assert response.json() == ["Kraków", "Warszawa"]


async def test_public_detail_includes_schedule_and_active_services(
    client: AsyncClient,
    workshop: Workshop,
    manager_token: str,
) -> None:
    headers = bearer(manager_token)
    await client.put(
        resource_url(workshop, "/opening-hours"),
        headers=headers,
        json={"days": [{"weekday": 1, "opens_at": "08:00", "closes_at": "16:00"}]},
    )
    await client.post(
        resource_url(workshop, "/closures"),
        headers=headers,
        json={"closed_on": "2099-12-24", "reason": "Wigilia"},
    )
    created = await client.post(
        resource_url(workshop, "/service-types"),
        headers=headers,
        json={"name": "Wymiana oleju", "duration_minutes": 60, "base_price_net": "100.00"},
    )
    hidden = await client.post(
        resource_url(workshop, "/service-types"),
        headers=headers,
        json={"name": "Usługa wycofana", "duration_minutes": 30, "base_price_net": "50.00"},
    )
    await client.patch(
        resource_url(workshop, f"/service-types/{hidden.json()['id']}"),
        headers=headers,
        json={"is_active": False},
    )

    response = await client.get(f"{WORKSHOPS_URL}/slug/{workshop.slug}")

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["opening_hours"] == [
        {"weekday": 1, "opens_at": "08:00:00", "closes_at": "16:00:00"}
    ]
    assert body["upcoming_closures"][0]["reason"] == "Wigilia"
    assert [service["id"] for service in body["service_types"]] == [created.json()["id"]]
    assert body["service_types"][0]["base_price_gross"] == "123.00"
    assert "tax_id" not in body


async def test_public_detail_of_inactive_workshop_is_not_found(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    inactive = await create_workshop(db_session, name="Nieczynny Serwis", is_active=False)

    response = await client.get(f"{WORKSHOPS_URL}/slug/{inactive.slug}")

    assert response.status_code == status.HTTP_404_NOT_FOUND


async def test_staff_detail_access_matrix(
    client: AsyncClient,
    db_session: AsyncSession,
    workshop: Workshop,
    other_workshop: Workshop,
    mechanic_token: str,
) -> None:
    await create_user(db_session, email="klient@example.com")
    client_token = await login(client, "klient@example.com")
    outsider_token = await staff_token(
        client, db_session, other_workshop, UserRole.MANAGER, "obcy@example.com"
    )
    await create_user(db_session, email="admin@example.com", role=UserRole.ADMIN)
    admin_token = await login(client, "admin@example.com")

    as_client = await client.get(resource_url(workshop), headers=bearer(client_token))
    as_outsider = await client.get(resource_url(workshop), headers=bearer(outsider_token))
    as_mechanic = await client.get(resource_url(workshop), headers=bearer(mechanic_token))
    as_admin = await client.get(resource_url(workshop), headers=bearer(admin_token))
    unknown = await client.get(
        f"{WORKSHOPS_URL}/{uuid.uuid4()}",
        headers=bearer(admin_token),
    )

    assert as_client.json()["error"]["code"] == "WORKSHOP_ACCESS_DENIED"
    assert as_outsider.status_code == status.HTTP_403_FORBIDDEN
    assert as_mechanic.status_code == status.HTTP_200_OK
    assert as_mechanic.json()["tax_id"] == workshop.tax_id
    assert as_admin.status_code == status.HTTP_200_OK
    assert unknown.status_code == status.HTTP_404_NOT_FOUND


async def test_manager_updates_workshop_but_mechanic_cannot(
    client: AsyncClient,
    workshop: Workshop,
    manager_token: str,
    mechanic_token: str,
) -> None:
    payload = {"phone": "+48 22 999 88 77", "name": "Auto Serwis Mokotów Plus"}

    as_mechanic = await client.patch(
        resource_url(workshop), headers=bearer(mechanic_token), json=payload
    )
    as_manager = await client.patch(
        resource_url(workshop), headers=bearer(manager_token), json=payload
    )

    assert as_mechanic.status_code == status.HTTP_403_FORBIDDEN
    assert as_manager.status_code == status.HTTP_200_OK
    assert as_manager.json()["phone"] == "+48 22 999 88 77"
    assert as_manager.json()["slug"] == workshop.slug


async def test_manager_cannot_change_activity_through_staff_endpoint(
    client: AsyncClient,
    workshop: Workshop,
    manager_token: str,
) -> None:
    response = await client.patch(
        resource_url(workshop),
        headers=bearer(manager_token),
        json={"is_active": False},
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


async def test_opening_hours_are_replaced_and_validated(
    client: AsyncClient,
    workshop: Workshop,
    manager_token: str,
) -> None:
    url = resource_url(workshop, "/opening-hours")
    headers = bearer(manager_token)
    await client.put(
        url,
        headers=headers,
        json={
            "days": [
                {"weekday": day, "opens_at": "08:00", "closes_at": "16:00"} for day in (1, 2, 3)
            ]
        },
    )

    replaced = await client.put(
        url,
        headers=headers,
        json={"days": [{"weekday": 6, "opens_at": "09:00", "closes_at": "13:00"}]},
    )
    invalid = await client.put(
        url,
        headers=headers,
        json={"days": [{"weekday": 8, "opens_at": "09:00", "closes_at": "13:00"}]},
    )

    assert [day["weekday"] for day in replaced.json()] == [6]
    assert invalid.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


async def test_closures_can_be_added_listed_and_removed(
    client: AsyncClient,
    workshop: Workshop,
    manager_token: str,
    mechanic_token: str,
) -> None:
    url = resource_url(workshop, "/closures")
    payload = {"closed_on": "2099-11-11", "reason": "Święto Niepodległości"}

    created = await client.post(url, headers=bearer(manager_token), json=payload)
    duplicate = await client.post(url, headers=bearer(manager_token), json=payload)
    by_mechanic = await client.post(
        url,
        headers=bearer(mechanic_token),
        json={"closed_on": "2099-12-25"},
    )
    listed = await client.get(url, headers=bearer(mechanic_token))
    deleted = await client.delete(f"{url}/{created.json()['id']}", headers=bearer(manager_token))
    deleted_again = await client.delete(
        f"{url}/{created.json()['id']}",
        headers=bearer(manager_token),
    )

    assert created.status_code == status.HTTP_201_CREATED
    assert duplicate.json()["error"]["code"] == "CLOSURE_ALREADY_EXISTS"
    assert by_mechanic.status_code == status.HTTP_403_FORBIDDEN
    assert [item["closed_on"] for item in listed.json()] == ["2099-11-11"]
    assert deleted.status_code == status.HTTP_204_NO_CONTENT
    assert deleted_again.status_code == status.HTTP_404_NOT_FOUND


async def test_past_closures_are_hidden_by_default(
    client: AsyncClient,
    workshop: Workshop,
    manager_token: str,
) -> None:
    url = resource_url(workshop, "/closures")
    await client.post(url, headers=bearer(manager_token), json={"closed_on": "2000-01-01"})

    upcoming = await client.get(url, headers=bearer(manager_token))
    historical = await client.get(
        url,
        headers=bearer(manager_token),
        params={"from_date": "1999-01-01"},
    )

    assert upcoming.json() == []
    assert len(historical.json()) == 1


async def test_bays_lifecycle(
    client: AsyncClient,
    workshop: Workshop,
    manager_token: str,
    mechanic_token: str,
) -> None:
    url = resource_url(workshop, "/bays")
    headers = bearer(manager_token)

    lift = await client.post(url, headers=headers, json={"name": "Podnośnik A", "type": "LIFT"})
    await client.post(url, headers=headers, json={"name": "Podnośnik B", "type": "LIFT"})
    duplicate = await client.post(
        url, headers=headers, json={"name": "Podnośnik A", "type": "GENERAL"}
    )
    rename_conflict = await client.patch(
        f"{url}/{lift.json()['id']}",
        headers=headers,
        json={"name": "Podnośnik B"},
    )
    deactivated = await client.patch(
        f"{url}/{lift.json()['id']}",
        headers=headers,
        json={"is_active": False},
    )
    active_only = await client.get(url, headers=bearer(mechanic_token))
    with_inactive = await client.get(
        url,
        headers=bearer(mechanic_token),
        params={"include_inactive": "true"},
    )
    missing = await client.patch(f"{url}/{uuid.uuid4()}", headers=headers, json={"name": "X"})

    assert lift.status_code == status.HTTP_201_CREATED
    assert duplicate.json()["error"]["code"] == "BAY_NAME_TAKEN"
    assert rename_conflict.json()["error"]["code"] == "BAY_NAME_TAKEN"
    assert deactivated.json()["is_active"] is False
    assert [bay["name"] for bay in active_only.json()] == ["Podnośnik B"]
    assert len(with_inactive.json()) == 2
    assert missing.status_code == status.HTTP_404_NOT_FOUND


async def test_service_types_lifecycle(
    client: AsyncClient,
    workshop: Workshop,
    manager_token: str,
) -> None:
    url = resource_url(workshop, "/service-types")
    headers = bearer(manager_token)
    payload = {"name": "Geometria kół", "duration_minutes": 60, "base_price_net": "179.00"}

    created = await client.post(url, headers=headers, json=payload)
    duplicate = await client.post(url, headers=headers, json=payload)
    invalid_vat = await client.post(
        url,
        headers=headers,
        json={**payload, "name": "Inna usługa", "vat_rate": "7"},
    )
    updated = await client.patch(
        f"{url}/{created.json()['id']}",
        headers=headers,
        json={"base_price_net": "199.00", "vat_rate": "8"},
    )
    missing = await client.patch(f"{url}/{uuid.uuid4()}", headers=headers, json={"name": "Nowa"})

    assert created.json()["vat_rate"] == "23.00"
    assert created.json()["base_price_gross"] == "220.17"
    assert duplicate.json()["error"]["code"] == "SERVICE_NAME_TAKEN"
    assert invalid_vat.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert updated.json()["base_price_gross"] == "214.92"
    assert missing.status_code == status.HTTP_404_NOT_FOUND


async def test_staff_lists_members_and_own_workshops(
    client: AsyncClient,
    workshop: Workshop,
    manager_token: str,
    mechanic_token: str,
) -> None:
    members = await client.get(resource_url(workshop, "/members"), headers=bearer(mechanic_token))
    my_workshops = await client.get("/api/v1/users/me/workshops", headers=bearer(manager_token))

    assert {member["role"] for member in members.json()} == {"MANAGER", "MECHANIC"}
    assert [item["id"] for item in my_workshops.json()] == [str(workshop.id)]


async def test_client_has_no_workshops(client: AsyncClient, db_session: AsyncSession) -> None:
    user: User = await create_user(db_session, email="klient@example.com")
    access_token = await login(client, user.email)

    response = await client.get("/api/v1/users/me/workshops", headers=bearer(access_token))

    assert response.json() == []
