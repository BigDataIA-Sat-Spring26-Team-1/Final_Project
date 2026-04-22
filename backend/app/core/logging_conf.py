"""Structured logging for CurateAI.

Cloud Run (and any modern container host) treats stdout + stderr as the log
transport, so this module writes everything there and leaves aggregation /
rotation / retention to the platform. Local dev gets coloured console output;
everything else emits single-line JSON that Cloud Logging ingests natively.
"""
import logging.config
import sys

import structlog


# Processors shared between structlog-native loggers and stdlib bridges.
# Keeping them in one list means a log line from `logging.getLogger(...)` ends
# up with the same shape as one from `structlog.get_logger(...)`.
_SHARED_PROCESSORS = [
    structlog.contextvars.merge_contextvars,
    structlog.stdlib.add_log_level,
    structlog.stdlib.add_logger_name,
    structlog.processors.TimeStamper(fmt="iso", utc=True),
    structlog.processors.StackInfoRenderer(),
    structlog.processors.format_exc_info,
    structlog.processors.CallsiteParameterAdder(
        [
            structlog.processors.CallsiteParameter.FILENAME,
            structlog.processors.CallsiteParameter.FUNC_NAME,
            structlog.processors.CallsiteParameter.LINENO,
            structlog.processors.CallsiteParameter.THREAD,
        ]
    ),
]


def setup_logging(app_env: str = "dev") -> None:
    """Wire up structlog + stdlib logging.

    In dev we favour a human-readable, coloured renderer. In any non-dev env
    (uat / prod / Cloud Run) we switch to JSON so log aggregators can parse
    fields like ``request_id`` and ``user_id`` without regex gymnastics.
    """
    is_dev = app_env.lower() == "dev"

    # Dev: colourised key=value output. Prod: compact JSON, one event per line.
    renderer = (
        structlog.dev.ConsoleRenderer(colors=True)
        if is_dev
        else structlog.processors.JSONRenderer()
    )

    structlog.configure(
        processors=_SHARED_PROCESSORS
        + [structlog.stdlib.ProcessorFormatter.wrap_for_formatter],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    root_level = "DEBUG" if is_dev else "INFO"

    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {
                    "()": structlog.stdlib.ProcessorFormatter,
                    "processor": renderer,
                    "foreign_pre_chain": _SHARED_PROCESSORS,
                },
            },
            "handlers": {
                # Stream to stdout. Cloud Run / Docker captures this for us.
                "stdout": {
                    "class": "logging.StreamHandler",
                    "formatter": "default",
                    "stream": sys.stdout,
                },
            },
            "loggers": {
                # Root logger — anything without an explicit handler inherits here.
                "": {"handlers": ["stdout"], "level": root_level},
                # App namespace stays at DEBUG in dev so we see internal flow.
                "app": {
                    "handlers": ["stdout"],
                    "level": "DEBUG" if is_dev else "INFO",
                    "propagate": False,
                },
                # Uvicorn emits via stdlib — redirect its three loggers to our
                # formatter so access logs look like the rest of the stream.
                "uvicorn": {"handlers": ["stdout"], "level": "INFO", "propagate": False},
                "uvicorn.error": {
                    "handlers": ["stdout"],
                    "level": "INFO",
                    "propagate": False,
                },
                "uvicorn.access": {
                    "handlers": ["stdout"],
                    "level": "INFO",
                    "propagate": False,
                },
            },
        }
    )


def get_logger(name: str = "app"):
    """Return a structlog logger bound to ``name``.

    Use the same name that stdlib logging would use (dotted module path) so
    filters and level overrides stay consistent across the stack.
    """
    return structlog.get_logger(name)
