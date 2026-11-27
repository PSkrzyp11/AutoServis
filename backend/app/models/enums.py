from enum import StrEnum


class UserRole(StrEnum):
    CLIENT = "CLIENT"
    MECHANIC = "MECHANIC"
    MANAGER = "MANAGER"
    ADMIN = "ADMIN"
