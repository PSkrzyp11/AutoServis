from arq.connections import RedisSettings
from arq.cron import cron
from arq.worker import func
from sqlalchemy.ext.asyncio import AsyncEngine

from app.core.config import get_settings
from app.core.database import create_engine, create_session_factory
from app.core.email import EmailRenderer, SmtpEmailSender
from app.core.logging import configure_logging, get_logger
from app.core.sentry import configure_sentry
from app.workers.queue import TaskName
from app.workers.tasks import (
    WorkerContext,
    send_due_appointment_reminders,
    send_email,
    send_password_reset_email,
)

MAX_TASK_TRIES = 5
REMINDER_MINUTES = frozenset({0, 15, 30, 45})

logger = get_logger()


async def startup(ctx: WorkerContext) -> None:
    settings = get_settings()
    configure_logging(settings)
    configure_sentry(settings)
    engine = create_engine(settings)
    ctx["settings"] = settings
    ctx["engine"] = engine
    ctx["session_factory"] = create_session_factory(engine)
    ctx["email_renderer"] = EmailRenderer()
    ctx["email_sender"] = SmtpEmailSender(settings)
    logger.info("worker_started", environment=settings.app_env.value)


async def shutdown(ctx: WorkerContext) -> None:
    engine: AsyncEngine = ctx["engine"]
    await engine.dispose()
    logger.info("worker_stopped")


class WorkerSettings:
    functions = (
        func(send_password_reset_email, name=TaskName.SEND_PASSWORD_RESET_EMAIL.value),
        func(send_email, name=TaskName.SEND_EMAIL.value),
    )
    cron_jobs = (cron(send_due_appointment_reminders, minute=set(REMINDER_MINUTES)),)
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = RedisSettings.from_dsn(get_settings().redis_url)
    max_tries = MAX_TASK_TRIES
