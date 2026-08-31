"""FastAPI entry point for the Swedish citizenship question service."""

from __future__ import annotations

import logging
import time
import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool

from app import __version__
from app.bedrock import (
    BedrockAuthenticationError,
    BedrockInvocationError,
    InvalidModelResponseError,
    close_bedrock_client,
    generate_question,
)
from app.config import settings
from app.logging import configure_logging
from app.schemas import QuestionResponse

configure_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Release shared clients when the container receives a stop signal."""
    yield
    await run_in_threadpool(close_bedrock_client)


def create_app() -> FastAPI:
    """Build the ASGI application."""
    docs_url = "/docs" if settings.docs_enabled else None
    openapi_url = "/openapi.json" if settings.docs_enabled else None
    application = FastAPI(
        title="Swedish Citizenship Question API",
        description=(
            "Generates Swedish citizenship test questions with Amazon Nova Lite."
        ),
        version=__version__,
        docs_url=docs_url,
        redoc_url=None,
        openapi_url=openapi_url,
        lifespan=lifespan,
    )

    @application.middleware("http")
    async def request_context(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        started_at = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            logger.exception(
                "Unhandled request failure",
                extra={"request_id": request_id, "path": request.url.path},
            )
            response = JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"detail": "An unexpected server error occurred."},
            )

        response.headers["X-Request-ID"] = request_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Cache-Control"] = "no-store"
        logger.info(
            "Request completed",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": round(
                    (time.perf_counter() - started_at) * 1000,
                    2,
                ),
            },
        )
        return response

    @application.get(
        "/health",
        status_code=status.HTTP_200_OK,
        summary="Container health check",
        include_in_schema=False,
    )
    async def health() -> dict[str, str]:
        return {"status": "ok", "version": __version__}

    @application.post(
        "/generate-question",
        response_model=QuestionResponse,
        status_code=status.HTTP_200_OK,
        summary="Generate one Swedish citizenship test question",
    )
    async def generate_question_endpoint() -> QuestionResponse:
        """Generate a question without blocking FastAPI's event loop."""
        try:
            return await run_in_threadpool(generate_question)
        except BedrockAuthenticationError as exc:
            logger.exception("AWS authentication or authorization failed")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="AWS authentication or Bedrock authorization failed.",
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
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="AWS Bedrock returned invalid generated content.",
            ) from exc

    return application


app = create_app()
