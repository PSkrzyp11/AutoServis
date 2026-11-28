import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Query, status

from app.api.dependencies import AppointmentServiceDep, CurrentUserDep, PageParamsDep
from app.schemas.appointment import (
    AppointmentCreate,
    AppointmentRead,
    AppointmentScope,
    AvailableSlotRead,
    DayAvailability,
)
from app.schemas.errors import error_responses
from app.schemas.pagination import Page

router = APIRouter(tags=["appointments"])

AUTH_ERRORS = (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)


@router.get(
    "/workshops/{workshop_id}/availability",
    summary="List free booking slots for a day",
    description=(
        "Public. Returns start times, every 15 minutes, when at least one suitable bay is free "
        "for the whole service duration. Days outside the booking horizon return no slots."
    ),
    responses=error_responses(status.HTTP_404_NOT_FOUND, status.HTTP_409_CONFLICT),
)
async def get_availability(
    workshop_id: uuid.UUID,
    appointment_service: AppointmentServiceDep,
    service_type_id: Annotated[uuid.UUID, Query(description="Service to book")],
    day: Annotated[date, Query(alias="date", description="Local date in the workshop time zone")],
) -> DayAvailability:
    result = await appointment_service.get_availability(workshop_id, service_type_id, day)
    return DayAvailability(
        day=result.day,
        service_type_id=result.service_type.id,
        duration_minutes=result.service_type.duration_minutes,
        slots=[
            AvailableSlotRead(start_at=slot.start_at, end_at=slot.end_at) for slot in result.slots
        ],
    )


@router.post(
    "/appointments",
    status_code=status.HTTP_201_CREATED,
    summary="Book an appointment",
    description=(
        "Books a slot returned by the availability endpoint. A free bay is assigned "
        "automatically and a confirmation email is sent."
    ),
    responses=error_responses(*AUTH_ERRORS, status.HTTP_404_NOT_FOUND, status.HTTP_409_CONFLICT),
)
async def book_appointment(
    payload: AppointmentCreate,
    user: CurrentUserDep,
    appointment_service: AppointmentServiceDep,
) -> AppointmentRead:
    return AppointmentRead.model_validate(await appointment_service.book(user, payload))


@router.get(
    "/appointments/mine",
    summary="List my appointments",
    description="Upcoming appointments are sorted from the nearest, past ones from the latest.",
    responses=error_responses(*AUTH_ERRORS),
)
async def list_my_appointments(
    user: CurrentUserDep,
    appointment_service: AppointmentServiceDep,
    page: PageParamsDep,
    scope: Annotated[AppointmentScope, Query(description="Which appointments to list")] = (
        AppointmentScope.UPCOMING
    ),
) -> Page[AppointmentRead]:
    appointments, total = await appointment_service.list_for_client(user, scope, page)
    return Page[AppointmentRead](
        items=[AppointmentRead.model_validate(item) for item in appointments],
        total=total,
        limit=page.limit,
        offset=page.offset,
    )


@router.post(
    "/appointments/{appointment_id}/cancel",
    summary="Cancel my appointment",
    description="Allowed for scheduled appointments until the configured deadline before start.",
    responses=error_responses(*AUTH_ERRORS, status.HTTP_404_NOT_FOUND, status.HTTP_409_CONFLICT),
)
async def cancel_my_appointment(
    appointment_id: uuid.UUID,
    user: CurrentUserDep,
    appointment_service: AppointmentServiceDep,
) -> AppointmentRead:
    appointment = await appointment_service.cancel_by_client(user, appointment_id)
    return AppointmentRead.model_validate(appointment)
