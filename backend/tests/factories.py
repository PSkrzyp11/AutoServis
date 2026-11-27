from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.core.text import slugify
from app.models.enums import UserRole
from app.models.user import User
from app.models.workshop import Workshop, WorkshopMember

DEFAULT_PASSWORD = "Sekretne-haslo-123"
LOGIN_URL = "/api/v1/auth/login"
VALID_TAX_ID = "5252389141"
SECOND_VALID_TAX_ID = "6793124584"


async def create_workshop(
    session: AsyncSession,
    *,
    name: str = "Auto Serwis Testowy",
    city: str = "Warszawa",
    is_active: bool = True,
) -> Workshop:
    workshop = Workshop(
        name=name,
        slug=slugify(name),
        tax_id=VALID_TAX_ID,
        street="ul. Testowa 1",
        postal_code="00-001",
        city=city,
        phone="+48 22 000 00 00",
        email="warsztat@example.com",
        is_active=is_active,
    )
    session.add(workshop)
    await session.commit()
    return workshop


async def assign_member(session: AsyncSession, workshop: Workshop, user: User) -> None:
    session.add(WorkshopMember(user_id=user.id, workshop_id=workshop.id))
    await session.commit()


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
