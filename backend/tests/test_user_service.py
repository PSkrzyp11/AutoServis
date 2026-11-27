import json
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.cli import export_openapi
from app.core.security import verify_password
from app.models.enums import UserRole
from app.services.user_service import UserService
from tests.factories import create_user


async def test_ensure_admin_creates_new_administrator(db_session: AsyncSession) -> None:
    user = await UserService(db_session).ensure_admin(
        email="admin@autoservis.pl",
        full_name="Administrator Platformy",
        password="Haslo-admina-123",
    )

    assert user.role is UserRole.ADMIN
    assert user.is_active is True
    assert user.password_hash is not None
    assert verify_password("Haslo-admina-123", user.password_hash)


async def test_ensure_admin_promotes_existing_account(db_session: AsyncSession) -> None:
    existing = await create_user(db_session, email="jan.kowalski@example.com", is_active=False)

    user = await UserService(db_session).ensure_admin(
        email="jan.kowalski@example.com",
        full_name="Jan Kowalski",
        password="Haslo-admina-123",
    )

    assert user.id == existing.id
    assert user.role is UserRole.ADMIN
    assert user.is_active is True


def test_export_openapi_writes_contract_with_error_codes(tmp_path: Path) -> None:
    output = tmp_path / "openapi.json"

    export_openapi(output)

    schema = json.loads(output.read_text(encoding="utf-8"))
    assert schema["info"]["title"] == "AutoServis API"
    assert "INVALID_CREDENTIALS" in schema["components"]["schemas"]["ErrorCode"]["enum"]
    assert "/api/v1/auth/login" in schema["paths"]
