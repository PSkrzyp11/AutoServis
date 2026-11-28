from zoneinfo import ZoneInfo

from app.models.appointment import Appointment

LOCAL_DATE_FORMAT = "%d.%m.%Y"
LOCAL_TIME_FORMAT = "%H:%M"


def build_appointment_email_context(appointment: Appointment) -> dict[str, str]:
    workshop = appointment.workshop
    timezone = ZoneInfo(workshop.timezone)
    local_start = appointment.start_at.astimezone(timezone)
    local_end = appointment.end_at.astimezone(timezone)
    vehicle = appointment.vehicle
    return {
        "full_name": appointment.client.full_name,
        "workshop_name": workshop.name,
        "workshop_address": f"{workshop.street}, {workshop.postal_code} {workshop.city}",
        "workshop_phone": workshop.phone,
        "service_name": appointment.service_type.name,
        "vehicle": f"{vehicle.make} {vehicle.model}, {vehicle.plate_number}",
        "date": local_start.strftime(LOCAL_DATE_FORMAT),
        "start_time": local_start.strftime(LOCAL_TIME_FORMAT),
        "end_time": local_end.strftime(LOCAL_TIME_FORMAT),
    }
