from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import Settings
from app.core.email import EmailRenderer, EmailSender, EmailTemplate
from app.core.logging import get_logger
from app.services.appointment_service import AppointmentReminderService

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


async def send_email(
    ctx: WorkerContext,
    *,
    template: str,
    recipient: str,
    context: dict[str, str],
) -> None:
    renderer: EmailRenderer = ctx["email_renderer"]
    sender: EmailSender = ctx["email_sender"]
    email_template = EmailTemplate(template)
    await sender.send(recipient=recipient, email=renderer.render(email_template, context))
    logger.info("email_sent", template=email_template.value)


async def send_due_appointment_reminders(ctx: WorkerContext) -> int:
    settings: Settings = ctx["settings"]
    session_factory: async_sessionmaker[AsyncSession] = ctx["session_factory"]
    renderer: EmailRenderer = ctx["email_renderer"]
    sender: EmailSender = ctx["email_sender"]

    async with session_factory() as session:
        reminders = await AppointmentReminderService(session, settings).claim_due_reminders()

    for reminder in reminders:
        recipient = reminder.pop("recipient")
        email = renderer.render(EmailTemplate.APPOINTMENT_REMINDER, reminder)
        await sender.send(recipient=recipient, email=email)
    logger.info("appointment_reminders_sent", count=len(reminders))
    return len(reminders)
