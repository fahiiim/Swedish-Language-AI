"""AWS Bedrock integration and model-response validation."""

from __future__ import annotations

import json
import logging
from threading import Lock
from typing import Any, Final

import boto3
from botocore.config import Config as BotoConfig
from botocore.exceptions import (
    BotoCoreError,
    ClientError,
    CredentialRetrievalError,
    NoCredentialsError,
    PartialCredentialsError,
)
from pydantic import ValidationError

from app.config import AWS_REGION, BEDROCK_MODEL_ID
from app.prompt import SYSTEM_PROMPT, USER_PROMPT
from app.schemas import QuestionResponse


logger = logging.getLogger(__name__)

_MAX_GENERATION_ATTEMPTS: Final[int] = 2
_REQUIRED_JSON_KEYS: Final[frozenset[str]] = frozenset(
    {"questionText", "options", "correctAnswer"}
)
_AUTH_ERROR_CODES: Final[frozenset[str]] = frozenset(
    {
        "AccessDeniedException",
        "ExpiredTokenException",
        "IncompleteSignature",
        "InvalidClientTokenId",
        "InvalidSignatureException",
        "SignatureDoesNotMatch",
        "UnauthorizedException",
        "UnrecognizedClientException",
    }
)
_CLIENT_CONFIG: Final[BotoConfig] = BotoConfig(
    connect_timeout=5,
    read_timeout=60,
    retries={"max_attempts": 3, "mode": "standard"},
)
_client: Any | None = None
_client_lock = Lock()


class BedrockAuthenticationError(RuntimeError):
    """Raised when AWS cannot authenticate or authorize the request."""


class BedrockInvocationError(RuntimeError):
    """Raised when Bedrock cannot complete an invocation."""


class InvalidModelResponseError(RuntimeError):
    """Raised when Bedrock repeatedly returns an invalid question."""


def _get_bedrock_client() -> Any:
    """Create one Bedrock Runtime client per application process."""
    global _client

    if _client is None:
        with _client_lock:
            if _client is None:
                _client = boto3.client(
                    "bedrock-runtime",
                    region_name=AWS_REGION,
                    config=_CLIENT_CONFIG,
                )

    return _client


def extract_json(text: str) -> dict[str, Any]:
    """Extract the first question-shaped JSON object from arbitrary text."""
    decoder = json.JSONDecoder()

    for index, character in enumerate(text):
        if character != "{":
            continue

        try:
            candidate, _ = decoder.raw_decode(text[index:])
        except json.JSONDecodeError:
            continue

        if isinstance(candidate, dict) and _REQUIRED_JSON_KEYS.issubset(candidate):
            return candidate

    raise ValueError("The model response did not contain a valid question JSON object")


def _response_text(response: dict[str, Any]) -> str:
    """Collect text blocks from a Bedrock Converse response."""
    try:
        content = response["output"]["message"]["content"]
    except (KeyError, TypeError):
        return ""

    if not isinstance(content, list):
        return ""

    return "\n".join(
        block["text"]
        for block in content
        if isinstance(block, dict) and isinstance(block.get("text"), str)
    )


def _invoke_model() -> str:
    """Invoke Amazon Nova through the Bedrock Converse API."""
    try:
        response = _get_bedrock_client().converse(
            modelId=BEDROCK_MODEL_ID,
            system=[{"text": SYSTEM_PROMPT}],
            messages=[
                {
                    "role": "user",
                    "content": [{"text": USER_PROMPT}],
                }
            ],
            inferenceConfig={"maxTokens": 300, "temperature": 0.8},
        )
    except (NoCredentialsError, PartialCredentialsError, CredentialRetrievalError) as exc:
        raise BedrockAuthenticationError(
            "AWS credentials are missing, incomplete, or unavailable."
        ) from exc
    except ClientError as exc:
        error_code = str(exc.response.get("Error", {}).get("Code", "Unknown"))
        if error_code in _AUTH_ERROR_CODES:
            raise BedrockAuthenticationError(
                f"AWS rejected the Bedrock credentials or permissions ({error_code})."
            ) from exc
        raise BedrockInvocationError(
            f"AWS Bedrock invocation failed ({error_code})."
        ) from exc
    except BotoCoreError as exc:
        raise BedrockInvocationError(
            "AWS Bedrock could not be reached or did not complete the request."
        ) from exc

    return _response_text(response)


def generate_question() -> QuestionResponse:
    """Generate and validate a question, retrying one invalid model response."""
    last_error: ValueError | ValidationError | None = None

    for attempt in range(1, _MAX_GENERATION_ATTEMPTS + 1):
        model_text = _invoke_model()
        try:
            return QuestionResponse.model_validate(extract_json(model_text))
        except (ValueError, ValidationError) as exc:
            last_error = exc
            logger.warning(
                "Invalid model response on attempt %d/%d (%s)",
                attempt,
                _MAX_GENERATION_ATTEMPTS,
                type(exc).__name__,
            )

    raise InvalidModelResponseError(
        "Bedrock returned an invalid question after two attempts."
    ) from last_error