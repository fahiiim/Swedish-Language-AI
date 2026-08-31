"""Typed application configuration loaded from environment variables."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from dotenv import load_dotenv

_ENV_FILE: Final[Path] = Path(__file__).resolve().parent.parent / ".env"
_LOCAL_CORS_PATTERN: Final[str] = r"^https?://(?:localhost|127\.0\.0\.1)(?::\d{1,5})?$"
_TRUE_VALUES: Final[frozenset[str]] = frozenset({"1", "true", "yes", "on"})


def _environment(name: str, default: str) -> str:
    """Read and normalize a non-empty environment variable."""
    return os.getenv(name, default).strip() or default


def _boolean_environment(name: str, default: bool) -> bool:
    """Read a conventional boolean environment variable."""
    raw_default = "true" if default else "false"
    return _environment(name, raw_default).casefold() in _TRUE_VALUES


def _integer_environment(
    name: str,
    default: int,
    *,
    minimum: int,
    maximum: int,
) -> int:
    """Read a bounded integer environment variable."""
    raw_value = _environment(name, str(default))
    try:
        value = int(raw_value)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer") from exc

    if not minimum <= value <= maximum:
        raise ValueError(f"{name} must be between {minimum} and {maximum}")
    return value


@dataclass(frozen=True, slots=True)
class Settings:
    """Immutable runtime settings."""

    app_environment: str
    aws_region: str
    bedrock_model_id: str
    bedrock_connect_timeout_seconds: int
    bedrock_read_timeout_seconds: int
    cors_origin_regex: str
    docs_enabled: bool
    log_level: str

    @property
    def is_production(self) -> bool:
        """Return whether production behavior should be enabled."""
        return self.app_environment.casefold() == "production"


def load_settings() -> Settings:
    """Load settings once and fail fast when configuration is malformed."""
    load_dotenv(dotenv_path=_ENV_FILE, override=False)

    settings = Settings(
        app_environment=_environment("APP_ENV", "development"),
        aws_region=_environment("AWS_REGION", "us-east-1"),
        bedrock_model_id=_environment("BEDROCK_MODEL_ID", "amazon.nova-lite-v1:0"),
        bedrock_connect_timeout_seconds=_integer_environment(
            "BEDROCK_CONNECT_TIMEOUT_SECONDS", 5, minimum=1, maximum=30
        ),
        bedrock_read_timeout_seconds=_integer_environment(
            "BEDROCK_READ_TIMEOUT_SECONDS", 60, minimum=5, maximum=300
        ),
        cors_origin_regex=_environment("CORS_ORIGIN_REGEX", _LOCAL_CORS_PATTERN),
        docs_enabled=_boolean_environment("DOCS_ENABLED", True),
        log_level=_environment("LOG_LEVEL", "INFO").upper(),
    )
    re.compile(settings.cors_origin_regex)
    return settings


settings: Final[Settings] = load_settings()
