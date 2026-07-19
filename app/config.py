"""Application configuration loaded from environment variables."""

import os
from pathlib import Path
from typing import Final

from dotenv import load_dotenv


_ENV_FILE: Final[Path] = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=_ENV_FILE, override=False)

AWS_REGION: Final[str] = os.getenv("AWS_REGION", "us-east-1").strip() or "us-east-1"

# Change this single value to use a different Bedrock model.
BEDROCK_MODEL_ID: Final[str] = "amazon.nova-lite-v1:0"

_LOCAL_CORS_PATTERN: Final[str] = (
	r"^https?://(?:localhost|127\.0\.0\.1|10\.10\.28\.\d{1,3})(?::\d{1,5})?$"
)
CORS_ORIGIN_REGEX: Final[str] = (
	os.getenv("CORS_ORIGIN_REGEX", _LOCAL_CORS_PATTERN).strip()
	or _LOCAL_CORS_PATTERN
)