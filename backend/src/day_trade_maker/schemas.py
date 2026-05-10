from datetime import UTC, datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator

from day_trade_maker.strategy_spec import StrategySpec

NonEmptyString = Annotated[str, Field(min_length=1)]


class TranscriptCreate(BaseModel):
    title: NonEmptyString
    source_url: str | None = None
    creator: str | None = None
    raw_text: NonEmptyString
    symbols: list[str] = Field(default_factory=list)
    timeframes: list[str] = Field(default_factory=list)

    @field_validator("title", "raw_text")
    @classmethod
    def reject_blank_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("must not be blank")
        return stripped

    @field_validator("symbols")
    @classmethod
    def normalize_symbols(cls, values: list[str]) -> list[str]:
        return [value.strip().upper() for value in values if value.strip()]

    @field_validator("timeframes")
    @classmethod
    def normalize_timeframes(cls, values: list[str]) -> list[str]:
        return [value.strip() for value in values if value.strip()]


class Transcript(TranscriptCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class StrategyCandidate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    transcript_id: int
    spec: StrategySpec
    status: str = "candidate"
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
