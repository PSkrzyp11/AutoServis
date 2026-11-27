import uuid
from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ConflictError, ErrorCode, NotFoundError
from app.core.logging import get_logger
from app.core.security import hash_password
from app.core.time import utc_now
from app.models.enums import UserRole
from app.models.user import User
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.repositories.user_repository import UserFilters, UserRepository, UserSorting
from app.schemas.pagination import PageParams
from app.schemas.user import AdminUserUpdate, UserProfileUpdate

logger = get_logger()


class UserService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._users = UserRepository(session)
        self._refresh_tokens = RefreshTokenRepository(session)

    async def get_user(self, user_id: uuid.UUID) -> User:
        user = await self._users.get_by_id(user_id)
        if user is None:
            raise NotFoundError("User not found")
        return user

    async def update_profile(self, user: User, data: UserProfileUpdate) -> User:
        if data.full_name is not None:
            user.full_name = data.full_name
        if "phone" in data.model_fields_set:
            user.phone = data.phone
        await self._session.commit()
        return user

    async def search_users(
        self,
        filters: UserFilters,
        sorting: UserSorting,
        page: PageParams,
    ) -> tuple[Sequence[User], int]:
        return await self._users.search(filters, sorting, page)

    async def update_user_as_admin(
        self,
        *,
        actor: User,
        user_id: uuid.UUID,
        data: AdminUserUpdate,
    ) -> User:
        if actor.id == user_id:
            raise ConflictError(
                ErrorCode.SELF_MODIFICATION_FORBIDDEN,
                "Administrators cannot change their own role or status",
            )

        user = await self.get_user(user_id)
        if data.role is not None:
            user.role = data.role
        if data.is_active is not None:
            user.is_active = data.is_active
            if not data.is_active:
                await self._refresh_tokens.revoke_all_for_user(user.id, utc_now())
        await self._session.commit()
        logger.info(
            "user_updated_by_admin",
            actor_id=str(actor.id),
            user_id=str(user.id),
            changes=data.model_dump(exclude_unset=True, mode="json"),
        )
        return user

    async def ensure_admin(self, *, email: str, full_name: str, password: str) -> User:
        user = await self._users.get_by_email(email)
        if user is None:
            user = User(email=email, full_name=full_name)
            self._users.add(user)
        user.role = UserRole.ADMIN
        user.is_active = True
        user.password_hash = hash_password(password)
        await self._session.commit()
        logger.info("admin_account_ensured", user_id=str(user.id))
        return user
