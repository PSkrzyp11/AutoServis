import uuid
from dataclasses import dataclass
from datetime import timedelta

import pytest
from fastapi import status
from httpx import AsyncClient, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.email import EmailTemplate
from app.core.time import utc_now
from app.models.appointment import Appointment
from app.models.enums import AppointmentStatus, UserRole
from app.models.user import User
from app.models.vehicle import Vehicle
from app.models.workshop import Workshop
from app.ws.events import RealtimeEventType, user_channel, workshop_channel
from tests.factories import (
    assign_member,
    bearer,
    create_bay,
    create_service_type,
    create_user,
    create_vehicle,
    create_workshop,
    login,
)
from tests.fakes import FakeEventPublisher, FakeTaskQueue

DIAGNOSIS = "Zużyte klocki hamulcowe osi przedniej, tarcze w dobrym stanie."


@dataclass
class OrderSetup:
    workshop: Workshop
    manager: User
    mechanic: User
    other_mechanic: User
    client_user: User
    vehicle: Vehicle
    appointment: Appointment
    manager_token: str
    mechanic_token: str
    other_token: str
    client_token: str

    @property
    def orders_url(self) -> str:
        return f"/api/v1/workshops/{self.workshop.id}/orders"


async def insert_scheduled_appointment(
    db_session: AsyncSession,
    workshop: Workshop,
    vehicle: Vehicle,
    client_user: User,
    hours_ahead: int,
) -> Appointment:
    bay = await create_bay(db_session, workshop, name=f"Podnośnik {hours_ahead}")
    service_type = await create_service_type(db_session, workshop, name=f"Usługa {hours_ahead}")
    start_at = utc_now() + timedelta(hours=hours_ahead)
    appointment = Appointment(
        workshop_id=workshop.id,
        bay_id=bay.id,
        vehicle_id=vehicle.id,
        client_id=client_user.id,
        service_type_id=service_type.id,
        start_at=start_at,
        end_at=start_at + timedelta(hours=1),
        status=AppointmentStatus.SCHEDULED,
        problem_description="Piszczy przy hamowaniu",
    )
    db_session.add(appointment)
    await db_session.commit()
    return appointment


@pytest.fixture
async def setup(client: AsyncClient, db_session: AsyncSession) -> OrderSetup:
    workshop = await create_workshop(db_session, name="Auto Serwis Mokotów")
    manager = await create_user(
        db_session,
        email="tomasz.wisniewski@example.com",
        full_name="Tomasz Wiśniewski",
        role=UserRole.MANAGER,
    )
    mechanic = await create_user(
        db_session,
        email="marek.kaminski@example.com",
        full_name="Marek Kamiński",
        role=UserRole.MECHANIC,
    )
    other_mechanic = await create_user(
        db_session,
        email="pawel.zielinski@example.com",
        full_name="Paweł Zieliński",
        role=UserRole.MECHANIC,
    )
    for member in (manager, mechanic, other_mechanic):
        await assign_member(db_session, workshop, member)
    client_user = await create_user(db_session, email="magdalena.jankowska@example.com")
    vehicle = await create_vehicle(db_session, client_user)
    appointment = await insert_scheduled_appointment(
        db_session,
        workshop,
        vehicle,
        client_user,
        hours_ahead=2,
    )
    return OrderSetup(
        workshop=workshop,
        manager=manager,
        mechanic=mechanic,
        other_mechanic=other_mechanic,
        client_user=client_user,
        vehicle=vehicle,
        appointment=appointment,
        manager_token=await login(client, manager.email),
        mechanic_token=await login(client, mechanic.email),
        other_token=await login(client, other_mechanic.email),
        client_token=await login(client, client_user.email),
    )


async def check_in(client: AsyncClient, setup: OrderSetup, appointment: Appointment) -> str:
    response = await client.post(
        f"/api/v1/workshops/{setup.workshop.id}/appointments/{appointment.id}/check-in",
        headers=bearer(setup.manager_token),
    )
    assert response.status_code == status.HTTP_200_OK, response.text
    order_id: str = response.json()["order"]["id"]
    return order_id


async def move(
    client: AsyncClient,
    setup: OrderSetup,
    order_id: str,
    token: str,
    step: tuple[str, str],
    *,
    note: str | None = None,
) -> Response:
    target, expected = step
    payload: dict[str, str] = {"status": target, "expected_status": expected}
    if note is not None:
        payload["note"] = note
    return await client.post(
        f"{setup.orders_url}/{order_id}/status",
        json=payload,
        headers=bearer(token),
    )


async def save_diagnosis(
    client: AsyncClient,
    setup: OrderSetup,
    order_id: str,
    token: str,
) -> Response:
    return await client.put(
        f"{setup.orders_url}/{order_id}/diagnosis",
        json={"diagnosis": DIAGNOSIS},
        headers=bearer(token),
    )


def order_emails(task_queue: FakeTaskQueue) -> list[str]:
    return [
        job.context["status"]
        for job in task_queue.emails
        if job.template is EmailTemplate.ORDER_STATUS_CHANGED
    ]


async def test_check_in_opens_order_and_notifies_client(
    client: AsyncClient,
    setup: OrderSetup,
    event_publisher: FakeEventPublisher,
    task_queue: FakeTaskQueue,
) -> None:
    order_id = await check_in(client, setup, setup.appointment)

    detail = await client.get(f"{setup.orders_url}/{order_id}", headers=bearer(setup.manager_token))
    notifications = await client.get(
        "/api/v1/notifications",
        headers=bearer(setup.client_token),
    )

    body = detail.json()
    assert body["status"] == "RECEIVED"
    assert body["mechanic"] is None
    assert body["appointment"]["problem_description"] == "Piszczy przy hamowaniu"
    assert body["allowed_transitions"] == ["DIAGNOSIS", "CANCELLED"]
    assert [(item["from_status"], item["to_status"]) for item in body["history"]] == [
        (None, "RECEIVED")
    ]
    assert body["history"][0]["changed_by"]["full_name"] == "Tomasz Wiśniewski"
    notification = notifications.json()["items"][0]
    assert notification["type"] == "ORDER_STATUS_CHANGED"
    assert notification["payload"]["to_status"] == "RECEIVED"
    assert notification["payload"]["vehicle"] == "Toyota Corolla, WA58213"
    assert notifications.json()["unread_count"] == 1
    published = {(item.channel, item.event.type) for item in event_publisher.published}
    assert published == {
        (workshop_channel(setup.workshop.id), RealtimeEventType.APPOINTMENT_CHANGED),
        (workshop_channel(setup.workshop.id), RealtimeEventType.ORDER_CHANGED),
        (user_channel(setup.client_user.id), RealtimeEventType.NOTIFICATION_CREATED),
    }
    assert order_emails(task_queue) == []


async def test_board_and_list_are_scoped_to_workshop_staff(
    client: AsyncClient,
    db_session: AsyncSession,
    setup: OrderSetup,
) -> None:
    order_id = await check_in(client, setup, setup.appointment)
    stranger = await create_user(db_session, email="obcy@example.com", role=UserRole.MECHANIC)
    stranger_token = await login(client, stranger.email)

    board = await client.get(f"{setup.orders_url}/board", headers=bearer(setup.mechanic_token))
    listed = await client.get(
        setup.orders_url,
        params={"status": ["RECEIVED", "DIAGNOSIS"], "unassigned": "true"},
        headers=bearer(setup.manager_token),
    )
    filtered_out = await client.get(
        setup.orders_url,
        params={"mechanic_id": str(setup.mechanic.id)},
        headers=bearer(setup.manager_token),
    )
    as_stranger = await client.get(f"{setup.orders_url}/board", headers=bearer(stranger_token))
    as_client = await client.get(f"{setup.orders_url}/board", headers=bearer(setup.client_token))

    assert [item["id"] for item in board.json()["items"]] == [order_id]
    assert board.json()["items"][0]["client"]["full_name"] == "Jan Kowalski"
    assert listed.json()["total"] == 1
    assert filtered_out.json()["total"] == 0
    assert as_stranger.json()["error"]["code"] == "WORKSHOP_ACCESS_DENIED"
    assert as_client.status_code == status.HTTP_403_FORBIDDEN


async def test_mechanic_takes_unassigned_order_by_moving_it(
    client: AsyncClient,
    setup: OrderSetup,
) -> None:
    order_id = await check_in(client, setup, setup.appointment)

    moved = await move(client, setup, order_id, setup.mechanic_token, ("DIAGNOSIS", "RECEIVED"))
    by_other = await move(client, setup, order_id, setup.other_token, ("CANCELLED", "DIAGNOSIS"))
    other_view = await client.get(
        f"{setup.orders_url}/{order_id}",
        headers=bearer(setup.other_token),
    )
    other_diagnosis = await save_diagnosis(client, setup, order_id, setup.other_token)

    assert moved.json()["mechanic"]["id"] == str(setup.mechanic.id)
    assert moved.json()["allowed_transitions"] == ["WAITING_FOR_APPROVAL", "CANCELLED"]
    assert by_other.status_code == status.HTTP_403_FORBIDDEN
    assert by_other.json()["error"]["code"] == "ORDER_NOT_ASSIGNED_TO_YOU"
    assert other_view.json()["allowed_transitions"] == []
    assert other_diagnosis.json()["error"]["code"] == "ORDER_NOT_ASSIGNED_TO_YOU"


async def test_manager_moving_order_does_not_take_it(
    client: AsyncClient,
    setup: OrderSetup,
) -> None:
    order_id = await check_in(client, setup, setup.appointment)

    moved = await move(client, setup, order_id, setup.manager_token, ("DIAGNOSIS", "RECEIVED"))

    assert moved.json()["status"] == "DIAGNOSIS"
    assert moved.json()["mechanic"] is None


async def test_conflicting_and_invalid_transitions_are_rejected(
    client: AsyncClient,
    setup: OrderSetup,
) -> None:
    order_id = await check_in(client, setup, setup.appointment)

    stale = await move(
        client, setup, order_id, setup.manager_token, ("WAITING_FOR_APPROVAL", "DIAGNOSIS")
    )
    skipped = await move(client, setup, order_id, setup.manager_token, ("READY", "RECEIVED"))
    unknown = await move(
        client, setup, str(uuid.uuid4()), setup.manager_token, ("DIAGNOSIS", "RECEIVED")
    )

    assert stale.status_code == status.HTTP_409_CONFLICT
    assert stale.json()["error"]["code"] == "ORDER_STATUS_CONFLICT"
    assert stale.json()["error"]["details"] == {"current_status": "RECEIVED"}
    assert skipped.json()["error"]["code"] == "INVALID_STATUS_TRANSITION"
    assert skipped.json()["error"]["details"] == {"from": "RECEIVED", "to": "READY"}
    assert unknown.status_code == status.HTTP_404_NOT_FOUND


async def test_full_workflow_records_history_and_emails_client(
    client: AsyncClient,
    setup: OrderSetup,
    task_queue: FakeTaskQueue,
) -> None:
    order_id = await check_in(client, setup, setup.appointment)
    token = setup.mechanic_token

    await move(client, setup, order_id, token, ("DIAGNOSIS", "RECEIVED"))
    without_diagnosis = await move(
        client, setup, order_id, token, ("WAITING_FOR_APPROVAL", "DIAGNOSIS")
    )
    diagnosis = await save_diagnosis(client, setup, order_id, token)
    steps = [
        ("WAITING_FOR_APPROVAL", "DIAGNOSIS", None),
        ("WAITING_FOR_PARTS", "WAITING_FOR_APPROVAL", "Klient zaakceptował telefonicznie"),
        ("IN_PROGRESS", "WAITING_FOR_PARTS", None),
        ("READY", "IN_PROGRESS", None),
        ("COMPLETED", "READY", None),
    ]
    responses = [
        await move(client, setup, order_id, token, (target, expected), note=note)
        for target, expected, note in steps
    ]
    after_close = await save_diagnosis(client, setup, order_id, token)

    assert without_diagnosis.json()["error"]["code"] == "DIAGNOSIS_REQUIRED"
    assert diagnosis.json()["diagnosis"] == DIAGNOSIS
    assert diagnosis.json()["has_diagnosis"] is True
    assert all(response.status_code == status.HTTP_200_OK for response in responses)
    final = responses[-1].json()
    assert final["status"] == "COMPLETED"
    assert final["closed_at"] is not None
    assert final["allowed_transitions"] == []
    assert [entry["to_status"] for entry in final["history"]] == [
        "RECEIVED",
        "DIAGNOSIS",
        "WAITING_FOR_APPROVAL",
        "WAITING_FOR_PARTS",
        "IN_PROGRESS",
        "READY",
        "COMPLETED",
    ]
    assert final["history"][3]["note"] == "Klient zaakceptował telefonicznie"
    assert order_emails(task_queue) == ["WAITING_FOR_APPROVAL", "READY"]
    assert after_close.json()["error"]["code"] == "ORDER_CLOSED"


async def test_cancelling_order_closes_it_and_emails_client(
    client: AsyncClient,
    setup: OrderSetup,
    task_queue: FakeTaskQueue,
) -> None:
    order_id = await check_in(client, setup, setup.appointment)

    cancelled = await move(
        client,
        setup,
        order_id,
        setup.manager_token,
        ("CANCELLED", "RECEIVED"),
        note="Klient zrezygnował",
    )
    board = await client.get(f"{setup.orders_url}/board", headers=bearer(setup.manager_token))

    assert cancelled.json()["status"] == "CANCELLED"
    assert cancelled.json()["closed_at"] is not None
    assert order_emails(task_queue) == ["CANCELLED"]
    assert task_queue.emails[-1].recipient == setup.client_user.email
    assert [item["status"] for item in board.json()["items"]] == ["CANCELLED"]


async def test_manager_assigns_mechanic_who_gets_notified(
    client: AsyncClient,
    db_session: AsyncSession,
    setup: OrderSetup,
) -> None:
    order_id = await check_in(client, setup, setup.appointment)
    outsider = await create_user(db_session, email="spoza@example.com", role=UserRole.MECHANIC)
    url = f"{setup.orders_url}/{order_id}/mechanic"

    assigned = await client.put(
        url,
        json={"mechanic_id": str(setup.other_mechanic.id)},
        headers=bearer(setup.manager_token),
    )
    not_member = await client.put(
        url,
        json={"mechanic_id": str(outsider.id)},
        headers=bearer(setup.manager_token),
    )
    by_mechanic = await client.put(
        url,
        json={"mechanic_id": str(setup.mechanic.id)},
        headers=bearer(setup.mechanic_token),
    )
    notifications = await client.get(
        "/api/v1/notifications",
        headers=bearer(setup.other_token),
    )
    unassigned = await client.put(
        url,
        json={"mechanic_id": None},
        headers=bearer(setup.manager_token),
    )

    assert assigned.json()["mechanic"]["full_name"] == "Paweł Zieliński"
    assert not_member.json()["error"]["code"] == "ASSIGNEE_NOT_IN_WORKSHOP"
    assert by_mechanic.json()["error"]["code"] == "WORKSHOP_ACCESS_DENIED"
    item = notifications.json()["items"][0]
    assert item["type"] == "ORDER_ASSIGNED"
    assert item["payload"]["assigned_by"] == "Tomasz Wiśniewski"
    assert item["payload"]["workshop_id"] == str(setup.workshop.id)
    assert unassigned.json()["mechanic"] is None


async def test_claiming_orders(client: AsyncClient, setup: OrderSetup) -> None:
    order_id = await check_in(client, setup, setup.appointment)
    url = f"{setup.orders_url}/{order_id}/claim"

    claimed = await client.post(url, headers=bearer(setup.mechanic_token))
    again = await client.post(url, headers=bearer(setup.mechanic_token))
    by_other = await client.post(url, headers=bearer(setup.other_token))

    assert claimed.json()["mechanic"]["id"] == str(setup.mechanic.id)
    assert again.status_code == status.HTTP_200_OK
    assert by_other.json()["error"]["code"] == "ORDER_ALREADY_ASSIGNED"


async def test_client_sees_own_orders_without_internal_notes(
    client: AsyncClient,
    db_session: AsyncSession,
    setup: OrderSetup,
) -> None:
    order_id = await check_in(client, setup, setup.appointment)
    await move(
        client, setup, order_id, setup.mechanic_token, ("DIAGNOSIS", "RECEIVED"), note="Notatka"
    )
    other_client = await create_user(db_session, email="piotr.mazur@example.com")
    other_token = await login(client, other_client.email)

    active = await client.get("/api/v1/orders/mine", headers=bearer(setup.client_token))
    closed = await client.get(
        "/api/v1/orders/mine",
        params={"scope": "closed"},
        headers=bearer(setup.client_token),
    )
    detail = await client.get(f"/api/v1/orders/{order_id}", headers=bearer(setup.client_token))
    foreign = await client.get(f"/api/v1/orders/{order_id}", headers=bearer(other_token))

    assert active.json()["total"] == 1
    assert active.json()["items"][0]["workshop"]["name"] == "Auto Serwis Mokotów"
    assert closed.json()["total"] == 0
    body = detail.json()
    assert body["status"] == "DIAGNOSIS"
    assert body["problem_description"] == "Piszczy przy hamowaniu"
    assert body["mechanic"]["full_name"] == "Marek Kamiński"
    assert [entry["to_status"] for entry in body["history"]] == ["RECEIVED", "DIAGNOSIS"]
    assert "note" not in body["history"][1]
    assert "changed_by" not in body["history"][1]
    assert foreign.status_code == status.HTTP_404_NOT_FOUND


async def test_appointment_lists_show_opened_order(
    client: AsyncClient,
    setup: OrderSetup,
) -> None:
    order_id = await check_in(client, setup, setup.appointment)

    mine = await client.get(
        "/api/v1/appointments/mine",
        params={"scope": "upcoming"},
        headers=bearer(setup.client_token),
    )

    order = mine.json()["items"][0]["order"]
    assert order["id"] == order_id
    assert order["status"] == "RECEIVED"
    assert order["number"] >= 1
