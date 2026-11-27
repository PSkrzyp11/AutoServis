import argparse
import asyncio
import getpass
import json
import sys
from dataclasses import asdict
from enum import StrEnum
from pathlib import Path

from pydantic import TypeAdapter, ValidationError

from app.core.config import Environment, Settings, get_settings
from app.core.database import create_engine, create_session_factory
from app.main import create_app
from app.schemas.common import FullName, NormalizedEmail, Password
from app.seed.demo_seeder import DemoSeeder, SeedSummary
from app.seed.schemas import load_seed_data
from app.services.user_service import UserService

EXIT_FAILURE = 1


class Command(StrEnum):
    CREATE_ADMIN = "create-admin"
    EXPORT_OPENAPI = "export-openapi"
    SEED_DEMO = "seed-demo"


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

    subcommands.add_parser(
        Command.SEED_DEMO.value,
        help="Insert demo workshops, staff, clients and vehicles. Safe to run repeatedly.",
    )
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


def resolve_demo_password(settings: Settings) -> str:
    if settings.app_env is Environment.PRODUCTION:
        message = "Demo data cannot be seeded in the production environment"
        raise RuntimeError(message)
    if settings.demo_user_password is None:
        message = "Set DEMO_USER_PASSWORD to seed demo data"
        raise RuntimeError(message)
    return TypeAdapter(Password).validate_python(settings.demo_user_password.get_secret_value())


async def seed_demo() -> SeedSummary:
    settings = get_settings()
    password = resolve_demo_password(settings)
    engine = create_engine(settings)
    session_factory = create_session_factory(engine)
    try:
        async with session_factory() as session:
            return await DemoSeeder(session, password).run(load_seed_data())
    finally:
        await engine.dispose()


def export_openapi(output: Path) -> None:
    schema = create_app().openapi()
    output.write_text(json.dumps(schema, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    sys.stdout.write(f"OpenAPI schema written to {output}\n")


def run_create_admin(arguments: argparse.Namespace) -> None:
    password = arguments.password or getpass.getpass("Password: ")
    asyncio.run(
        create_admin(email=arguments.email, full_name=arguments.full_name, password=password)
    )


def run_seed_demo() -> None:
    summary = asyncio.run(seed_demo())
    for name, count in asdict(summary).items():
        sys.stdout.write(f"{name}: {count}\n")


def main() -> None:
    arguments = build_parser().parse_args()
    command = Command(arguments.command)
    try:
        if command is Command.EXPORT_OPENAPI:
            export_openapi(arguments.output)
        elif command is Command.SEED_DEMO:
            run_seed_demo()
        else:
            run_create_admin(arguments)
    except (ValidationError, RuntimeError) as error:
        sys.stderr.write(f"{error}\n")
        sys.exit(EXIT_FAILURE)


if __name__ == "__main__":
    main()
