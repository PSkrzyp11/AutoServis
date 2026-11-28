from app.models.enums import OrderStatus
from app.models.service_order import ServiceOrder


def describe_vehicle(order: ServiceOrder) -> str:
    vehicle = order.appointment.vehicle
    return f"{vehicle.make} {vehicle.model}, {vehicle.plate_number}"


def build_order_email_context(order: ServiceOrder, status: OrderStatus) -> dict[str, str]:
    workshop = order.appointment.workshop
    return {
        "full_name": order.appointment.client.full_name,
        "workshop_name": workshop.name,
        "workshop_phone": workshop.phone,
        "order_number": str(order.number),
        "vehicle": describe_vehicle(order),
        "service_name": order.appointment.service_type.name,
        "status": status.value,
    }
