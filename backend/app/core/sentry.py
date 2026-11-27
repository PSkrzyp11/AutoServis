import sentry_sdk

from app.core.config import Settings

TRACES_SAMPLE_RATE = 0.1


def configure_sentry(settings: Settings) -> None:
    if not settings.sentry_dsn:
        return
    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        environment=settings.app_env.value,
        traces_sample_rate=TRACES_SAMPLE_RATE,
    )
