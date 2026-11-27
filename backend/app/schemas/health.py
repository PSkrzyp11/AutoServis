from enum import StrEnum

from pydantic import BaseModel, Field


class ComponentStatus(StrEnum):
    OK = "ok"
    UNAVAILABLE = "unavailable"


class HealthResponse(BaseModel):
    status: ComponentStatus = Field(description="Aggregated status of the service")
    components: dict[str, ComponentStatus] = Field(
        default_factory=dict,
        description="Status of each dependency checked by the probe",
    )
