"""API contract tests that do not call AWS."""

import pytest
from fastapi.testclient import TestClient

from app.bedrock import (
    BedrockAuthenticationError,
    BedrockInvocationError,
    InvalidModelResponseError,
)
from app.main import app
from tests.test_bedrock import VALID_QUESTION


def test_health_endpoint() -> None:
    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-request-id"]


def test_generate_question_contract(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(
        "app.main.generate_question",
        lambda: VALID_QUESTION,
    )

    with TestClient(app) as client:
        response = client.post("/generate-question")

    assert response.status_code == 200
    assert response.json() == VALID_QUESTION


@pytest.mark.parametrize(
    ("error", "expected_status"),
    [
        (BedrockAuthenticationError("denied"), 503),
        (BedrockInvocationError("unavailable"), 502),
        (InvalidModelResponseError("invalid"), 502),
    ],
)
def test_generate_question_maps_upstream_errors(
    monkeypatch: pytest.MonkeyPatch,
    error: RuntimeError,
    expected_status: int,
) -> None:
    def raise_upstream_error() -> None:
        raise error

    monkeypatch.setattr(
        "app.main.generate_question",
        raise_upstream_error,
    )

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post("/generate-question")

    assert response.status_code == expected_status
    assert "denied" not in response.text
