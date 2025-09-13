from __future__ import annotations

import logging
import sys
from typing import Literal

import structlog

from mcg_agent.config import get_settings


def _configure_logging(level: str, fmt: Literal["json", "text"]) -> None:
    """Configure stdlib + structlog logging according to settings."""
    log_level = getattr(logging, level.upper(), logging.INFO)

    if fmt == "json":
        processors = [
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.EventRenamer("message"),
            structlog.processors.dict_tracebacks,
            structlog.processors.JSONRenderer(),
        ]
    else:
        processors = [
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.dev.ConsoleRenderer(colors=True),
        ]

    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=log_level,
    )

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
        cache_logger_on_first_use=True,
    )


def setup_logging() -> None:
    settings = get_settings()
    _configure_logging(settings.server.LOG_LEVEL, settings.server.LOG_FORMAT)


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    logger = structlog.get_logger()
    return logger.bind(logger=name) if name else logger


__all__ = ["setup_logging", "get_logger"]

