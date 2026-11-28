from enum import IntEnum, StrEnum


class UserRole(StrEnum):
    CLIENT = "CLIENT"
    MECHANIC = "MECHANIC"
    MANAGER = "MANAGER"
    ADMIN = "ADMIN"


STAFF_ROLES = frozenset({UserRole.MECHANIC, UserRole.MANAGER})


class BayType(StrEnum):
    GENERAL = "GENERAL"
    LIFT = "LIFT"
    DIAGNOSTIC = "DIAGNOSTIC"
    TIRES = "TIRES"


class AppointmentStatus(StrEnum):
    SCHEDULED = "SCHEDULED"
    CHECKED_IN = "CHECKED_IN"
    CANCELLED = "CANCELLED"
    NO_SHOW = "NO_SHOW"


ACTIVE_APPOINTMENT_STATUSES = frozenset({AppointmentStatus.SCHEDULED, AppointmentStatus.CHECKED_IN})


class OrderStatus(StrEnum):
    RECEIVED = "RECEIVED"
    DIAGNOSIS = "DIAGNOSIS"
    WAITING_FOR_APPROVAL = "WAITING_FOR_APPROVAL"
    WAITING_FOR_PARTS = "WAITING_FOR_PARTS"
    IN_PROGRESS = "IN_PROGRESS"
    READY = "READY"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


CLOSED_ORDER_STATUSES = frozenset({OrderStatus.COMPLETED, OrderStatus.CANCELLED})


class NotificationType(StrEnum):
    ORDER_STATUS_CHANGED = "ORDER_STATUS_CHANGED"
    ORDER_ASSIGNED = "ORDER_ASSIGNED"


class IsoWeekday(IntEnum):
    MONDAY = 1
    TUESDAY = 2
    WEDNESDAY = 3
    THURSDAY = 4
    FRIDAY = 5
    SATURDAY = 6
    SUNDAY = 7
