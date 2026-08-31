"""Unit tests for Bedrock response parsing."""

import json

import pytest
from pydantic import ValidationError

from app import bedrock
from app.bedrock import extract_json
from app.schemas import QuestionResponse

VALID_QUESTION = {
    "questionText": "Vilken stad är Sveriges huvudstad?",
    "options": {
        "A": "Stockholm",
        "B": "Göteborg",
        "C": "Malmö",
        "D": "Uppsala",
    },
    "correctAnswer": "A",
}


def test_extract_json_from_surrounding_model_text() -> None:
    text = f"Generated result:\n{VALID_QUESTION!r}".replace("'", '"')

    assert extract_json(text) == VALID_QUESTION


def test_extract_json_rejects_unrelated_object() -> None:
    with pytest.raises(ValueError, match="question JSON object"):
        extract_json('{"message": "no question"}')


def test_question_options_must_be_unique() -> None:
    duplicate_options = {
        **VALID_QUESTION,
        "options": {**VALID_QUESTION["options"], "D": " stockholm "},
    }

    with pytest.raises(ValidationError, match="must be unique"):
        QuestionResponse.model_validate(duplicate_options)


def test_generate_question_retries_invalid_content(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    responses = iter(["not json", json.dumps(VALID_QUESTION)])
    monkeypatch.setattr(bedrock, "_invoke_model", lambda: next(responses))

    result = bedrock.generate_question()

    assert result.model_dump(by_alias=True) == VALID_QUESTION
