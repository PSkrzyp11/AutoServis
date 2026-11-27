from app.schemas.bay import BayRead
from app.schemas.service_type import ServiceTypeRead
from app.schemas.workshop import (
    ClosureRead,
    OpeningHoursEntry,
    WorkshopMemberRead,
    WorkshopPublicDetail,
    WorkshopRead,
    WorkshopStaffDetail,
    WorkshopSummary,
)
from app.services.workshop_service import (
    WorkshopMemberView,
    WorkshopPublicView,
    WorkshopStaffView,
)


def to_public_detail(view: WorkshopPublicView) -> WorkshopPublicDetail:
    summary = WorkshopSummary.model_validate(view.workshop)
    return WorkshopPublicDetail(
        **summary.model_dump(),
        email=view.workshop.email,
        opening_hours=[OpeningHoursEntry.model_validate(day) for day in view.opening_hours],
        upcoming_closures=[ClosureRead.model_validate(item) for item in view.upcoming_closures],
        service_types=[ServiceTypeRead.model_validate(item) for item in view.service_types],
    )


def to_staff_detail(view: WorkshopStaffView) -> WorkshopStaffDetail:
    workshop = WorkshopRead.model_validate(view.workshop)
    return WorkshopStaffDetail(
        **workshop.model_dump(),
        opening_hours=[OpeningHoursEntry.model_validate(day) for day in view.opening_hours],
        bays=[BayRead.model_validate(bay) for bay in view.bays],
    )


def to_member_read(view: WorkshopMemberView) -> WorkshopMemberRead:
    return WorkshopMemberRead(
        user_id=view.user.id,
        full_name=view.user.full_name,
        email=view.user.email,
        phone=view.user.phone,
        role=view.user.role,
        joined_at=view.joined_at,
    )
