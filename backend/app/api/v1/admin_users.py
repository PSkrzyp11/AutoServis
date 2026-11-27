import uuid
from typing import Annotated

from fastapi import APIRouter, Query, status

from app.api.dependencies import AdminUserDep, PageParamsDep, UserServiceDep
from app.models.enums import UserRole
from app.repositories.user_repository import UserFilters, UserSorting
from app.schemas.errors import error_responses
from app.schemas.pagination import Page, SortOrder
from app.schemas.user import AdminUserUpdate, UserRead, UserSortField

SEARCH_MAX_LENGTH = 100

router = APIRouter(prefix="/admin/users", tags=["admin"])

ADMIN_ERROR_RESPONSES = error_responses(status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)


@router.get(
    "",
    summary="List users",
    description="Paginated list of all platform users with filtering and sorting.",
    responses=ADMIN_ERROR_RESPONSES,
)
async def list_users(
    *,
    _admin: AdminUserDep,
    user_service: UserServiceDep,
    page: PageParamsDep,
    role: Annotated[UserRole | None, Query(description="Filter by role")] = None,
    is_active: Annotated[bool | None, Query(description="Filter by account status")] = None,
    search: Annotated[
        str | None,
        Query(max_length=SEARCH_MAX_LENGTH, description="Case-insensitive email or name match"),
    ] = None,
    sort_by: Annotated[UserSortField, Query(description="Field used for sorting")] = (
        UserSortField.CREATED_AT
    ),
    sort_order: Annotated[SortOrder, Query(description="Sorting direction")] = SortOrder.DESC,
) -> Page[UserRead]:
    users, total = await user_service.search_users(
        UserFilters(role=role, is_active=is_active, search=search),
        UserSorting(field=sort_by, order=sort_order),
        page,
    )
    return Page[UserRead](
        items=[UserRead.model_validate(user) for user in users],
        total=total,
        limit=page.limit,
        offset=page.offset,
    )


@router.get(
    "/{user_id}",
    summary="Get a user",
    responses=error_responses(
        status.HTTP_401_UNAUTHORIZED,
        status.HTTP_403_FORBIDDEN,
        status.HTTP_404_NOT_FOUND,
    ),
)
async def get_user(
    user_id: uuid.UUID,
    _admin: AdminUserDep,
    user_service: UserServiceDep,
) -> UserRead:
    user = await user_service.get_user(user_id)
    return UserRead.model_validate(user)


@router.patch(
    "/{user_id}",
    summary="Change a user's role or status",
    description="Deactivating an account also signs the user out of all sessions.",
    responses=error_responses(
        status.HTTP_401_UNAUTHORIZED,
        status.HTTP_403_FORBIDDEN,
        status.HTTP_404_NOT_FOUND,
        status.HTTP_409_CONFLICT,
    ),
)
async def update_user(
    user_id: uuid.UUID,
    payload: AdminUserUpdate,
    admin: AdminUserDep,
    user_service: UserServiceDep,
) -> UserRead:
    user = await user_service.update_user_as_admin(actor=admin, user_id=user_id, data=payload)
    return UserRead.model_validate(user)
