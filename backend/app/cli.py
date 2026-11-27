import argparse
import asyncio
import getpass
import json
import sys
from enum import StrEnum
from pathlib import Path

from pydantic import TypeAdapter, ValidationError

from app.core.config import get_settings
from app.core.database import create_engine, create_session_factory
from app.main import create_app
from app.schemas.common import FullName, NormalizedEmail, Password
from app.services.user_service import UserService

EXIT_FAILURE = 1


class Command(StrEnum):
    CREATE_ADMIN = "create-admin"
    EXPORT_OPENAPI = "export-openapi"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m app.cli", description="AutoServis tools")
    subcommands = parser.add_subparsers(dest="command", required=True)

    create_admin = subcommands.add_parser(
        Command.CREATE_ADMIN.value,
        help="Create an administrator or promote an existing account",
    )
    create_admin.add_argument("--email", required=True)
    create_admin.add_argument("--full-name", required=True)
    create_admin.add_argument(
        "--password",
        help="Password for the account. Prompted interactively when omitted.",
    )

    export_openapi = subcommands.add_parser(
        Command.EXPORT_OPENAPI.value,
        help="Write the OpenAPI schema to a JSON file",
    )
    export_openapi.add_argument("--output", type=Path, default=Path("openapi.json"))
    return parser


async def create_admin(*, email: str, full_name: str, password: str) -> None:
    settings = get_settings()
    engine = create_engine(settings)
    session_factory = create_session_factory(engine)
    try:
        async with session_factory() as session:
            user = await UserService(session).ensure_admin(
                email=TypeAdapter(NormalizedEmail).validate_python(email),
                full_name=TypeAdapter(FullName).validate_python(full_name),
                password=TypeAdapter(Password).validate_python(password),
            )
    finally:
        await engine.dispose()
    sys.stdout.write(f"Administrator account ready: {user.email}\n")


def export_openapi(output: Path) -> None:
    schema = create_app().openapi()
    output.write_text(json.dumps(schema, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    sys.stdout.write(f"OpenAPI schema written to {output}\n")


def main() -> None:
    arguments = build_parser().parse_args()
    command = Command(arguments.command)
    if command is Command.EXPORT_OPENAPI:
        export_openapi(arguments.output)
        return

    password = arguments.password or getpass.getpass("Password: ")
    try:
        asyncio.run(
            create_admin(email=arguments.email, full_name=arguments.full_name, password=password)
        )
    except ValidationError as error:
        sys.stderr.write(f"Invalid input: {error}\n")
        sys.exit(EXIT_FAILURE)


if __name__ == "__main__":
    main()
