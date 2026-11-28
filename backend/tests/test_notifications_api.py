import uuid
from datetime import timedelta

from fastapi import status
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.time import utc_now
from app.models.enums import NotificationType, OrderStatus
from app.models.notification import Notification
from app.models.user import User
from tests.factories import bearer, create_user, login

NOTIFICATIONS_URL = "/api/v1/notifications"


async def add_notifications(db_session: AsyncSession, user: User, count: int) -> list[Notification]:
    now = utc_now()
    notifications = [
        Notification(
            user_id=user.id,
            type=NotificationType.ORDER_STATUS_CHANGED,
            payload={
                "order_id": str(uuid.uuid4()),
                "order_number": index + 1,
                "workshop_name": "Auto Serwis Mokotów",
                "vehicle": "Toyota Corolla, WA58213",
                "from_status": OrderStatus.RECEIVED.value,
                "to_status": OrderStatus.DIAGNOSIS.value,
            },
            created_at=now + timedelta(minutes=index),
        )
        for index in range(count)
    ]
    db_session.add_all(notifications)
    await db_session.commit()
    return notifications


async def test_list_count_and_mark_notifications(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    user = await create_user(db_session)
    notifications = await add_notifications(db_session, user, 3)
    token = await login(client, user.email)

    first_page = await client.get(NOTIFICATIONS_URL, params={"limit": 2}, headers=bearer(token))
    marked = await client.post(
        f"{NOTIFICATIONS_URL}/{notifications[0].id}/read",
        headers=bearer(token),
    )
    marked_again = await client.post(
        f"{NOTIFICATIONS_URL}/{notifications[0].id}/read",
        headers=bearer(token),
    )
    unread = await client.get(
        NOTIFICATIONS_URL,
        params={"unread_only": "true"},
        headers=bearer(token),
    )
    count = await client.get(f"{NOTIFICATIONS_URL}/unread-count", headers=bearer(token))
    read_all = await client.post(f"{NOTIFICATIONS_URL}/read-all", headers=bearer(token))
    count_after = await client.get(f"{NOTIFICATIONS_URL}/unread-count", headers=bearer(token))

    page = first_page.json()
    assert page["total"] == 3
    assert page["unread_count"] == 3
    assert [item["payload"]["order_number"] for item in page["items"]] == [3, 2]
    assert marked.json()["read_at"] is not None
    assert marked_again.json()["read_at"] == marked.json()["read_at"]
    assert unread.json()["total"] == 2
    assert count.json() == {"unread_count": 2}
    assert read_all.status_code == status.HTTP_204_NO_CONTENT
    assert count_after.json() == {"unread_count": 0}


async def test_notifications_are_private(client: AsyncClient, db_session: AsyncSession) -> None:
    owner = await create_user(db_session)
    other = await create_user(db_session, email="piotr.mazur@example.com")
    notifications = await add_notifications(db_session, owner, 1)
    other_token = await login(client, other.email)

    listed = await client.get(NOTIFICATIONS_URL, headers=bearer(other_token))
    marked = await client.post(
        f"{NOTIFICATIONS_URL}/{notifications[0].id}/read",
        headers=bearer(other_token),
    )
    anonymous = await client.get(NOTIFICATIONS_URL)

    assert listed.json()["total"] == 0
    assert marked.status_code == status.HTTP_404_NOT_FOUND
    assert anonymous.status_code == status.HTTP_401_UNAUTHORIZED
