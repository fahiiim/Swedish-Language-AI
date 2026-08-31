"""Structured logging suitable for local terminals and CloudWatch Logs."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any

from app.config import settings

_STANDARD_LOG_RECORD_KEYS = frozenset(logging.makeLogRecord({}).__dict__)


class JsonFormatter(logging.Formatter):
    """Format log records as one JSON object per line."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        payload.update(
            {
                key: value
                for key, value in record.__dict__.items()
                if key not in _STANDARD_LOG_RECORD_KEYS
                and key not in {"message", "asctime"}
                and isinstance(value, (str, int, float, bool, type(None)))
            }
        )
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def configure_logging() -> None:
    """Install a single process-wide logging configuration."""
    handler = logging.StreamHandler()
    if settings.is_production:
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
        )

    logging.basicConfig(
        level=settings.log_level,
        handlers=[handler],
        force=True,
    )
