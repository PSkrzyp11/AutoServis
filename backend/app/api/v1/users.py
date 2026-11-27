from fastapi import APIRouter, status

from app.api.dependencies import CurrentUserDep, UserServiceDep, WorkshopServiceDep
from app.schemas.errors import error_responses
from app.schemas.user import UserProfileUpdate, UserRead
from app.schemas.workshop import WorkshopSummary

router = APIRouter(prefix="/users", tags=["users"])


@router.get(
    "/me",
    summary="Get the current user",
    responses=error_responses(status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN),
)
async def get_me(user: CurrentUserDep) -> UserRead:
    return UserRead.model_validate(user)


@router.patch(
    "/me",
    summary="Update the current user's profile",
    responses=error_responses(status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN),
)
async def update_me(
    payload: UserProfileUpdate,
    user: CurrentUserDep,
    user_service: UserServiceDep,
) -> UserRead:
    updated_user = await user_service.update_profile(user, payload)
    return UserRead.model_validate(updated_user)


@router.get(
    "/me/workshops",
    summary="List workshops I work in",
    description="Returns the workshops a mechanic or manager is assigned to.",
    responses=error_responses(status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN),
)
async def list_my_workshops(
    user: CurrentUserDep,
    workshop_service: WorkshopServiceDep,
) -> list[WorkshopSummary]:
    workshops = await workshop_service.list_for_member(user)
    return [WorkshopSummary.model_validate(workshop) for workshop in workshops]
