import uuid
from collections.abc import Awaitable, Callable
from typing import Annotated

import structlog
from fastapi import Depends, Query, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.dependencies import RedisDep, SessionDep, SettingsDep, TaskQueueDep
from app.core.errors import ErrorCode, ForbiddenError, UnauthorizedError
from app.core.rate_limit import RateLimiter, RateLimitRule
from app.models.enums import UserRole
from app.models.user import User
from app.models.workshop import Workshop
from app.schemas.pagination import PageParams
from app.services.auth_service import AuthService
from app.services.password_reset_service import PasswordResetService
from app.services.user_service import UserService
from app.services.vehicle_service import VehicleService
from app.services.workshop_resource_service import BayService, ServiceTypeService
from app.services.workshop_schedule_service import WorkshopScheduleService
from app.services.workshop_service import WorkshopPermission, WorkshopService

DEFAULT_PAGE_LIMIT = 20
MAX_PAGE_LIMIT = 100
UNKNOWN_CLIENT_IDENTIFIER = "unknown"

LOGIN_RATE_LIMIT = RateLimitRule(scope="login", limit=10, window_seconds=60)
REGISTER_RATE_LIMIT = RateLimitRule(scope="register", limit=10, window_seconds=600)
PASSWORD_RESET_RATE_LIMIT = RateLimitRule(scope="password_reset", limit=5, window_seconds=900)

bearer_scheme = HTTPBearer(
    auto_error=False,
    description="Access token returned by the login and refresh endpoints",
)


def get_auth_service(session: SessionDep, settings: SettingsDep) -> AuthService:
    return AuthService(session, settings)


def get_password_reset_service(
    session: SessionDep,
    settings: SettingsDep,
    task_queue: TaskQueueDep,
) -> PasswordResetService:
    return PasswordResetService(session, settings, task_queue)


def get_user_service(session: SessionDep) -> UserService:
    return UserService(session)


def get_workshop_service(session: SessionDep) -> WorkshopService:
    return WorkshopService(session)


def get_workshop_schedule_service(session: SessionDep) -> WorkshopScheduleService:
    return WorkshopScheduleService(session)


def get_bay_service(session: SessionDep) -> BayService:
    return BayService(session)


def get_service_type_service(session: SessionDep) -> ServiceTypeService:
    return ServiceTypeService(session)


def get_vehicle_service(session: SessionDep) -> VehicleService:
    return VehicleService(session)


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]
PasswordResetServiceDep = Annotated[PasswordResetService, Depends(get_password_reset_service)]
UserServiceDep = Annotated[UserService, Depends(get_user_service)]
WorkshopServiceDep = Annotated[WorkshopService, Depends(get_workshop_service)]
WorkshopScheduleServiceDep = Annotated[
    WorkshopScheduleService,
    Depends(get_workshop_schedule_service),
]
BayServiceDep = Annotated[BayService, Depends(get_bay_service)]
ServiceTypeServiceDep = Annotated[ServiceTypeService, Depends(get_service_type_service)]
VehicleServiceDep = Annotated[VehicleService, Depends(get_vehicle_service)]


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    auth_service: AuthServiceDep,
) -> User:
    if credentials is None:
        raise UnauthorizedError(ErrorCode.UNAUTHORIZED, "Authentication required")
    user = await auth_service.get_user_from_access_token(credentials.credentials)
    structlog.contextvars.bind_contextvars(user_id=str(user.id))
    return user


CurrentUserDep = Annotated[User, Depends(get_current_user)]


def require_roles(*allowed_roles: UserRole) -> Callable[[User], Awaitable[User]]:
    async def ensure_role(user: CurrentUserDep) -> User:
        if user.role not in allowed_roles:
            raise ForbiddenError(ErrorCode.FORBIDDEN, "Insufficient permissions")
        return user

    return ensure_role


AdminUserDep = Annotated[User, Depends(require_roles(UserRole.ADMIN))]


def workshop_with_permission(
    permission: WorkshopPermission,
) -> Callable[[uuid.UUID, User, WorkshopService], Awaitable[Workshop]]:
    async def resolve_workshop(
        workshop_id: uuid.UUID,
        user: CurrentUserDep,
        workshop_service: WorkshopServiceDep,
    ) -> Workshop:
        return await workshop_service.get_accessible_workshop(user, workshop_id, permission)

    return resolve_workshop


StaffWorkshopDep = Annotated[
    Workshop,
    Depends(workshop_with_permission(WorkshopPermission.VIEW)),
]
ManagedWorkshopDep = Annotated[
    Workshop,
    Depends(workshop_with_permission(WorkshopPermission.MANAGE)),
]


def get_page_params(
    limit: Annotated[
        int,
        Query(ge=1, le=MAX_PAGE_LIMIT, description="Maximum number of items to return"),
    ] = DEFAULT_PAGE_LIMIT,
    offset: Annotated[int, Query(ge=0, description="Number of items to skip")] = 0,
) -> PageParams:
    return PageParams(limit=limit, offset=offset)


PageParamsDep = Annotated[PageParams, Depends(get_page_params)]


def rate_limited(rule: RateLimitRule) -> Callable[[Request, RedisDep], Awaitable[None]]:
    async def enforce_rate_limit(request: Request, redis: RedisDep) -> None:
        identifier = request.client.host if request.client else UNKNOWN_CLIENT_IDENTIFIER
        await RateLimiter(redis).hit(rule, identifier)

    return enforce_rate_limit
