import logging
import json
import sys
from datetime import datetime, timezone
from app.core.config import settings


class StructuredJSONFormatter(logging.Formatter):
    """
    Emits every log record as a single-line JSON object.
    Compatible with CloudWatch, Datadog, and any log aggregator.
    """

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "service": settings.APP_NAME,
            "environment": settings.APP_ENV,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Attach exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        # Attach any extra fields passed via extra={} in log calls
        for key, value in record.__dict__.items():
            if key not in (
                "message", "asctime", "created", "exc_info", "exc_text",
                "filename", "funcName", "id", "levelname", "levelno",
                "lineno", "module", "msecs", "msg", "name", "pathname",
                "process", "processName", "relativeCreated", "stack_info",
                "thread", "threadName", "args",
            ):
                log_entry[key] = value

        return json.dumps(log_entry, default=str)


def setup_logging() -> None:
    """
    Configures root logger. Call once at application startup in main.py.
    In development: human-readable. In production: structured JSON.
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    handler = logging.StreamHandler(sys.stdout)

    if settings.is_development:
        handler.setFormatter(
            logging.Formatter(
                fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )
    else:
        handler.setFormatter(StructuredJSONFormatter())

    root_logger.handlers.clear()
    root_logger.addHandler(handler)

    # Silence noisy third-party loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)