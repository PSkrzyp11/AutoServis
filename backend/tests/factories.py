from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.enums import UserRole
from app.models.user import User

DEFAULT_PASSWORD = "Sekretne-haslo-123"
LOGIN_URL = "/api/v1/auth/login"


async def create_user(
    session: AsyncSession,
    *,
    email: str = "jan.kowalski@example.com",
    password: str = DEFAULT_PASSWORD,
    full_name: str = "Jan Kowalski",
    role: UserRole = UserRole.CLIENT,
    is_active: bool = True,
) -> User:
    user = User(
        email=email,
        password_hash=hash_password(password),
        full_name=full_name,
        role=role,
        is_active=is_active,
    )
    session.add(user)
    await session.commit()
    return user


async def login(client: AsyncClient, email: str, password: str = DEFAULT_PASSWORD) -> str:
    response = await client.post(LOGIN_URL, json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    access_token: str = response.json()["access_token"]
    return access_token


def bearer(access_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {access_token}"}


def refresh_cookie_header(refresh_token: str) -> dict[str, str]:
    return {"Cookie": f"refresh_token={refresh_token}"}
