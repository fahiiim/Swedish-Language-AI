"""Pydantic models for API responses."""

from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator


class QuestionOptions(BaseModel):
    """The four answer choices for a generated question."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    a: str = Field(alias="A", min_length=1)
    b: str = Field(alias="B", min_length=1)
    c: str = Field(alias="C", min_length=1)
    d: str = Field(alias="D", min_length=1)

    @model_validator(mode="after")
    def options_must_be_unique(self) -> Self:
        normalized = {option.casefold() for option in (self.a, self.b, self.c, self.d)}
        if len(normalized) != 4:
            raise ValueError("All answer options must be unique")
        return self


class QuestionResponse(BaseModel):
    """A validated Swedish citizenship test question."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    question_text: str = Field(alias="questionText", min_length=1)
    options: QuestionOptions
    correct_answer: Literal["A", "B", "C", "D"] = Field(alias="correctAnswer")