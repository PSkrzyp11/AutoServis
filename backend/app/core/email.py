from collections.abc import Mapping
from dataclasses import dataclass
from email.message import EmailMessage
from enum import StrEnum
from pathlib import Path
from typing import Protocol

import aiosmtplib
from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape

from app.core.config import Settings

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
DEFAULT_LOCALE = "pl"


class EmailTemplate(StrEnum):
    PASSWORD_RESET = "password_reset"
    APPOINTMENT_CONFIRMATION = "appointment_confirmation"
    APPOINTMENT_REMINDER = "appointment_reminder"
    ORDER_STATUS_CHANGED = "order_status_changed"


@dataclass(frozen=True)
class RenderedEmail:
    subject: str
    text_body: str
    html_body: str


class EmailRenderer:
    def __init__(self, locale: str = DEFAULT_LOCALE, templates_dir: Path = TEMPLATES_DIR) -> None:
        self._environment = Environment(
            loader=FileSystemLoader(templates_dir / locale / "email"),
            autoescape=select_autoescape(enabled_extensions=("html",)),
            undefined=StrictUndefined,
            keep_trailing_newline=True,
        )

    def render(self, template: EmailTemplate, context: Mapping[str, object]) -> RenderedEmail:
        return RenderedEmail(
            subject=self._render_file(f"{template.value}/subject.txt", context).strip(),
            text_body=self._render_file(f"{template.value}/body.txt", context),
            html_body=self._render_file(f"{template.value}/body.html", context),
        )

    def _render_file(self, path: str, context: Mapping[str, object]) -> str:
        return self._environment.get_template(path).render(context)


class EmailSender(Protocol):
    async def send(self, *, recipient: str, email: RenderedEmail) -> None: ...


class SmtpEmailSender:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def send(self, *, recipient: str, email: RenderedEmail) -> None:
        message = EmailMessage()
        message["From"] = self._settings.mail_from
        message["To"] = recipient
        message["Subject"] = email.subject
        message.set_content(email.text_body)
        message.add_alternative(email.html_body, subtype="html")

        password = self._settings.smtp_password
        await aiosmtplib.send(
            message,
            hostname=self._settings.smtp_host,
            port=self._settings.smtp_port,
            username=self._settings.smtp_username,
            password=password.get_secret_value() if password else None,
            start_tls=self._settings.smtp_use_tls,
        )
