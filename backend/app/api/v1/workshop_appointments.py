import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Query, status

from app.api.dependencies import AppointmentServiceDep, StaffWorkshopDep
from app.models.enums import AppointmentStatus
from app.schemas.appointment import StaffAppointmentRead
from app.schemas.errors import error_responses

router = APIRouter(prefix="/workshops/{workshop_id}/appointments", tags=["appointments"])

STAFF_ERRORS = (
    status.HTTP_401_UNAUTHORIZED,
    status.HTTP_403_FORBIDDEN,
    status.HTTP_404_NOT_FOUND,
)
TRANSITION_ERRORS = error_responses(*STAFF_ERRORS, status.HTTP_409_CONFLICT)


@router.get(
    "",
    summary="List workshop appointments in a date range",
    description="Local dates in the workshop time zone, inclusive, at most 31 days.",
    responses=error_responses(*STAFF_ERRORS),
)
async def list_workshop_appointments(
    workshop: StaffWorkshopDep,
    appointment_service: AppointmentServiceDep,
    from_date: Annotated[date, Query(description="First local date")],
    to_date: Annotated[date, Query(description="Last local date")],
) -> list[StaffAppointmentRead]:
    appointments = await appointment_service.list_for_workshop(workshop, from_date, to_date)
    return [StaffAppointmentRead.model_validate(item) for item in appointments]


@router.post(
    "/{appointment_id}/check-in",
    summary="Mark that the vehicle arrived",
    responses=TRANSITION_ERRORS,
)
async def check_in_appointment(
    appointment_id: uuid.UUID,
    workshop: StaffWorkshopDep,
    appointment_service: AppointmentServiceDep,
) -> StaffAppointmentRead:
    appointment = await appointment_service.change_status_by_staff(
        workshop,
        appointment_id,
        AppointmentStatus.CHECKED_IN,
    )
    return StaffAppointmentRead.model_validate(appointment)


@router.post(
    "/{appointment_id}/no-show",
    summary="Mark that the client did not arrive",
    description="Allowed only after the appointment start time.",
    responses=TRANSITION_ERRORS,
)
async def mark_no_show(
    appointment_id: uuid.UUID,
    workshop: StaffWorkshopDep,
    appointment_service: AppointmentServiceDep,
) -> StaffAppointmentRead:
    appointment = await appointment_service.change_status_by_staff(
        workshop,
        appointment_id,
        AppointmentStatus.NO_SHOW,
    )
    return StaffAppointmentRead.model_validate(appointment)


@router.post(
    "/{appointment_id}/cancel",
    summary="Cancel an appointment on behalf of the workshop",
    responses=TRANSITION_ERRORS,
)
async def cancel_workshop_appointment(
    appointment_id: uuid.UUID,
    workshop: StaffWorkshopDep,
    appointment_service: AppointmentServiceDep,
) -> StaffAppointmentRead:
    appointment = await appointment_service.change_status_by_staff(
        workshop,
        appointment_id,
        AppointmentStatus.CANCELLED,
    )
    return StaffAppointmentRead.model_validate(appointment)
