from arq.connections import RedisSettings
from arq.worker import func

from app.core.config import get_settings
from app.core.email import EmailRenderer, SmtpEmailSender
from app.core.logging import configure_logging, get_logger
from app.core.sentry import configure_sentry
from app.workers.queue import TaskName
from app.workers.tasks import WorkerContext, send_password_reset_email

MAX_TASK_TRIES = 5

logger = get_logger()


async def startup(ctx: WorkerContext) -> None:
    settings = get_settings()
    configure_logging(settings)
    configure_sentry(settings)
    ctx["settings"] = settings
    ctx["email_renderer"] = EmailRenderer()
    ctx["email_sender"] = SmtpEmailSender(settings)
    logger.info("worker_started", environment=settings.app_env.value)


class WorkerSettings:
    functions = (func(send_password_reset_email, name=TaskName.SEND_PASSWORD_RESET_EMAIL.value),)
    on_startup = startup
    redis_settings = RedisSettings.from_dsn(get_settings().redis_url)
    max_tries = MAX_TASK_TRIES
