"""FastAPI entry point for the Swedish citizenship question service."""

import asyncio
import logging

from fastapi import FastAPI, HTTPException, status

from app.bedrock import (
    BedrockAuthenticationError,
    BedrockInvocationError,
    InvalidModelResponseError,
    generate_question as generate_bedrock_question,
)
from app.schemas import QuestionResponse


logger = logging.getLogger(__name__)

app = FastAPI(
    title="Swedish Citizenship Question API",
    description="Generates Swedish citizenship test questions with Amazon Nova Lite.",
    version="1.0.0",
)


@app.post(
    "/generate-question",
    response_model=QuestionResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate one Swedish citizenship test question",
)
async def generate_question() -> QuestionResponse:
    """Generate a question without blocking FastAPI's event loop."""
    try:
        return await asyncio.to_thread(generate_bedrock_question)
    except BedrockAuthenticationError as exc:
        logger.exception("AWS authentication or authorization failed")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "AWS authentication or authorization failed. "
                "Check credentials and Bedrock permissions."
            ),
        ) from exc
    except BedrockInvocationError as exc:
        logger.exception("AWS Bedrock invocation failed")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AWS Bedrock could not generate a question. Try again later.",
        ) from exc
    except InvalidModelResponseError as exc:
        logger.exception("AWS Bedrock returned invalid generated content")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="AWS Bedrock returned an invalid question after one retry.",
        ) from exc
    except Exception as exc:
        logger.exception("Unexpected question generation failure")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while generating the question.",
        ) from exc