from typing import Any

from app.models.service_order import ServiceOrder
from app.models.user import User
from app.schemas.appointment import AppointmentVehicle, AppointmentWorkshop
from app.schemas.order import (
    ClientOrderDetail,
    ClientOrderHistoryEntry,
    ClientOrderRead,
    OrderAppointment,
    OrderClient,
    OrderHistoryEntry,
    OrderPerson,
    OrderServiceType,
    StaffOrderDetail,
    StaffOrderSummary,
)
from app.services.order_workflow import available_transitions


def summary_fields(order: ServiceOrder, viewer: User) -> dict[str, Any]:
    appointment = order.appointment
    return {
        "id": order.id,
        "number": order.number,
        "status": order.status,
        "status_changed_at": order.status_changed_at,
        "created_at": order.created_at,
        "closed_at": order.closed_at,
        "has_diagnosis": bool(order.diagnosis),
        "vehicle": AppointmentVehicle.model_validate(appointment.vehicle),
        "client": OrderClient.model_validate(appointment.client),
        "service": OrderServiceType.model_validate(appointment.service_type),
        "mechanic": OrderPerson.model_validate(order.mechanic) if order.mechanic else None,
        "appointment": OrderAppointment(
            id=appointment.id,
            start_at=appointment.start_at,
            end_at=appointment.end_at,
            bay_name=appointment.bay.name,
            problem_description=appointment.problem_description,
        ),
        "allowed_transitions": available_transitions(
            order.status,
            viewer.role,
            viewer.id,
            order.mechanic_id,
        ),
    }


def to_staff_summary(order: ServiceOrder, viewer: User) -> StaffOrderSummary:
    return StaffOrderSummary(**summary_fields(order, viewer))


def to_staff_detail(order: ServiceOrder, viewer: User) -> StaffOrderDetail:
    return StaffOrderDetail(
        **summary_fields(order, viewer),
        diagnosis=order.diagnosis,
        history=[OrderHistoryEntry.model_validate(entry) for entry in order.history],
    )


def client_fields(order: ServiceOrder) -> dict[str, Any]:
    appointment = order.appointment
    return {
        "id": order.id,
        "number": order.number,
        "status": order.status,
        "status_changed_at": order.status_changed_at,
        "created_at": order.created_at,
        "closed_at": order.closed_at,
        "workshop": AppointmentWorkshop.model_validate(appointment.workshop),
        "vehicle": AppointmentVehicle.model_validate(appointment.vehicle),
        "service": OrderServiceType.model_validate(appointment.service_type),
        "appointment_start_at": appointment.start_at,
        "mechanic": OrderPerson.model_validate(order.mechanic) if order.mechanic else None,
    }


def to_client_read(order: ServiceOrder) -> ClientOrderRead:
    return ClientOrderRead(**client_fields(order))


def to_client_detail(order: ServiceOrder) -> ClientOrderDetail:
    return ClientOrderDetail(
        **client_fields(order),
        diagnosis=order.diagnosis,
        problem_description=order.appointment.problem_description,
        history=[ClientOrderHistoryEntry.model_validate(entry) for entry in order.history],
    )
