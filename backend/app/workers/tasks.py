from typing import Any

from app.core.config import Settings
from app.core.email import EmailRenderer, EmailSender, EmailTemplate
from app.core.logging import get_logger

logger = get_logger()

WorkerContext = dict[str, Any]


async def send_password_reset_email(
    ctx: WorkerContext,
    *,
    recipient: str,
    full_name: str,
    reset_url: str,
) -> None:
    settings: Settings = ctx["settings"]
    renderer: EmailRenderer = ctx["email_renderer"]
    sender: EmailSender = ctx["email_sender"]

    email = renderer.render(
        EmailTemplate.PASSWORD_RESET,
        {
            "full_name": full_name,
            "reset_url": reset_url,
            "expires_in_minutes": settings.password_reset_token_ttl_minutes,
        },
    )
    await sender.send(recipient=recipient, email=email)
    logger.info("password_reset_email_sent")
