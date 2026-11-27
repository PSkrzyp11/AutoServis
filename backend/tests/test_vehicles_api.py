import uuid

import pytest
from fastapi import status
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.factories import bearer, create_user, login

VEHICLES_URL = "/api/v1/vehicles"
VEHICLE_PAYLOAD = {
    "make": "Skoda",
    "model": "Octavia",
    "production_year": 2017,
    "plate_number": "we 3k721",
    "vin": "tmbjj7ne8h0218734",
    "mileage_km": 164200,
    "engine": "2.0 TDI",
}


@pytest.fixture
async def owner_token(client: AsyncClient, db_session: AsyncSession) -> str:
    await create_user(db_session, email="piotr.mazur@example.com")
    return await login(client, "piotr.mazur@example.com")


@pytest.fixture
async def other_token(client: AsyncClient, db_session: AsyncSession) -> str:
    await create_user(db_session, email="ewa.grabowska@example.com")
    return await login(client, "ewa.grabowska@example.com")


async def test_create_vehicle_normalizes_identifiers(
    client: AsyncClient,
    owner_token: str,
) -> None:
    response = await client.post(VEHICLES_URL, headers=bearer(owner_token), json=VEHICLE_PAYLOAD)

    assert response.status_code == status.HTTP_201_CREATED
    assert response.json()["plate_number"] == "WE3K721"
    assert response.json()["vin"] == "TMBJJ7NE8H0218734"


async def test_vin_must_be_unique_among_active_vehicles(
    client: AsyncClient,
    owner_token: str,
    other_token: str,
) -> None:
    created = await client.post(VEHICLES_URL, headers=bearer(owner_token), json=VEHICLE_PAYLOAD)

    duplicate = await client.post(VEHICLES_URL, headers=bearer(other_token), json=VEHICLE_PAYLOAD)
    await client.delete(f"{VEHICLES_URL}/{created.json()['id']}", headers=bearer(owner_token))
    after_sale = await client.post(VEHICLES_URL, headers=bearer(other_token), json=VEHICLE_PAYLOAD)

    assert duplicate.status_code == status.HTTP_409_CONFLICT
    assert duplicate.json()["error"]["code"] == "VIN_ALREADY_REGISTERED"
    assert after_sale.status_code == status.HTTP_201_CREATED


async def test_vehicle_without_vin_is_allowed(client: AsyncClient, owner_token: str) -> None:
    payload = {key: value for key, value in VEHICLE_PAYLOAD.items() if key != "vin"}

    response = await client.post(VEHICLES_URL, headers=bearer(owner_token), json=payload)

    assert response.status_code == status.HTTP_201_CREATED
    assert response.json()["vin"] is None


async def test_owner_sees_only_own_vehicles(
    client: AsyncClient,
    owner_token: str,
    other_token: str,
) -> None:
    own = await client.post(VEHICLES_URL, headers=bearer(owner_token), json=VEHICLE_PAYLOAD)
    await client.post(
        VEHICLES_URL,
        headers=bearer(other_token),
        json={**VEHICLE_PAYLOAD, "vin": None, "plate_number": "KR4F21C"},
    )

    listed = await client.get(VEHICLES_URL, headers=bearer(owner_token))
    foreign = await client.get(f"{VEHICLES_URL}/{own.json()['id']}", headers=bearer(other_token))

    assert [vehicle["id"] for vehicle in listed.json()["items"]] == [own.json()["id"]]
    assert listed.json()["total"] == 1
    assert foreign.status_code == status.HTTP_404_NOT_FOUND


async def test_update_can_clear_optional_fields(client: AsyncClient, owner_token: str) -> None:
    created = await client.post(VEHICLES_URL, headers=bearer(owner_token), json=VEHICLE_PAYLOAD)
    url = f"{VEHICLES_URL}/{created.json()['id']}"

    updated = await client.patch(
        url,
        headers=bearer(owner_token),
        json={"vin": None, "mileage_km": 170000, "make": None},
    )
    fetched = await client.get(url, headers=bearer(owner_token))

    assert updated.json()["vin"] is None
    assert updated.json()["mileage_km"] == 170000
    assert updated.json()["make"] == "Skoda"
    assert fetched.json() == updated.json()


async def test_update_rejects_vin_of_another_vehicle(
    client: AsyncClient,
    owner_token: str,
) -> None:
    await client.post(VEHICLES_URL, headers=bearer(owner_token), json=VEHICLE_PAYLOAD)
    second = await client.post(
        VEHICLES_URL,
        headers=bearer(owner_token),
        json={**VEHICLE_PAYLOAD, "vin": None, "plate_number": "WI7742F"},
    )

    response = await client.patch(
        f"{VEHICLES_URL}/{second.json()['id']}",
        headers=bearer(owner_token),
        json={"vin": VEHICLE_PAYLOAD["vin"]},
    )

    assert response.json()["error"]["code"] == "VIN_ALREADY_REGISTERED"


async def test_deleted_vehicle_disappears(client: AsyncClient, owner_token: str) -> None:
    created = await client.post(VEHICLES_URL, headers=bearer(owner_token), json=VEHICLE_PAYLOAD)
    url = f"{VEHICLES_URL}/{created.json()['id']}"

    deleted = await client.delete(url, headers=bearer(owner_token))
    fetched = await client.get(url, headers=bearer(owner_token))
    listed = await client.get(VEHICLES_URL, headers=bearer(owner_token))
    missing = await client.delete(f"{VEHICLES_URL}/{uuid.uuid4()}", headers=bearer(owner_token))

    assert deleted.status_code == status.HTTP_204_NO_CONTENT
    assert fetched.status_code == status.HTTP_404_NOT_FOUND
    assert listed.json()["total"] == 0
    assert missing.status_code == status.HTTP_404_NOT_FOUND


async def test_invalid_vehicle_payload_reports_fields(
    client: AsyncClient,
    owner_token: str,
) -> None:
    response = await client.post(
        VEHICLES_URL,
        headers=bearer(owner_token),
        json={**VEHICLE_PAYLOAD, "vin": "123", "plate_number": "1", "production_year": 1800},
    )

    fields = {item["field"] for item in response.json()["error"]["details"]["fields"]}
    assert fields == {"vin", "plate_number", "production_year"}


async def test_vehicles_require_authentication(client: AsyncClient) -> None:
    response = await client.get(VEHICLES_URL)

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
