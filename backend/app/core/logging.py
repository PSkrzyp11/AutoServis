import logging

import structlog
from structlog.typing import FilteringBoundLogger, Processor

from app.core.config import Settings


def configure_logging(settings: Settings) -> None:
    processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
    ]
    if settings.log_json:
        processors.extend(
            [structlog.processors.dict_tracebacks, structlog.processors.JSONRenderer()]
        )
    else:
        processors.append(structlog.dev.ConsoleRenderer())

    minimum_level = logging.getLevelNamesMapping()[settings.log_level.value]
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(minimum_level),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger() -> FilteringBoundLogger:
    logger: FilteringBoundLogger = structlog.get_logger()
    return logger
