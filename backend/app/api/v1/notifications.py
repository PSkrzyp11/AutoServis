import uuid
from typing import Annotated

from fastapi import APIRouter, Query, status

from app.api.dependencies import CurrentUserDep, NotificationServiceDep, PageParamsDep
from app.schemas.errors import error_responses
from app.schemas.notification import (
    NotificationPage,
    NotificationRead,
    UnreadNotificationCount,
    to_notification_read,
)

router = APIRouter(prefix="/notifications", tags=["notifications"])

AUTH_ERRORS = (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)


@router.get(
    "",
    summary="List my notifications",
    description="Newest first, with the number of unread notifications.",
    responses=error_responses(*AUTH_ERRORS),
)
async def list_notifications(
    user: CurrentUserDep,
    notification_service: NotificationServiceDep,
    page: PageParamsDep,
    unread_only: Annotated[bool, Query(description="Only unread notifications")] = False,
) -> NotificationPage:
    notifications, total = await notification_service.list_for_user(
        user,
        unread_only=unread_only,
        page=page,
    )
    return NotificationPage(
        items=[to_notification_read(item) for item in notifications],
        total=total,
        limit=page.limit,
        offset=page.offset,
        unread_count=await notification_service.count_unread(user),
    )


@router.get(
    "/unread-count",
    summary="Count my unread notifications",
    responses=error_responses(*AUTH_ERRORS),
)
async def count_unread_notifications(
    user: CurrentUserDep,
    notification_service: NotificationServiceDep,
) -> UnreadNotificationCount:
    return UnreadNotificationCount(unread_count=await notification_service.count_unread(user))


@router.post(
    "/{notification_id}/read",
    summary="Mark a notification as read",
    responses=error_responses(*AUTH_ERRORS, status.HTTP_404_NOT_FOUND),
)
async def mark_notification_read(
    notification_id: uuid.UUID,
    user: CurrentUserDep,
    notification_service: NotificationServiceDep,
) -> NotificationRead:
    notification = await notification_service.mark_read(user, notification_id)
    return to_notification_read(notification)


@router.post(
    "/read-all",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Mark all my notifications as read",
    responses=error_responses(*AUTH_ERRORS),
)
async def mark_all_notifications_read(
    user: CurrentUserDep,
    notification_service: NotificationServiceDep,
) -> None:
    await notification_service.mark_all_read(user)
