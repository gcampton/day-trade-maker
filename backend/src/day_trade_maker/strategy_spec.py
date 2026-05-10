from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class StrictSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")


class IndicatorSpec(StrictSchema):
    name: str = Field(min_length=1)
    parameters: dict[str, Any] = Field(default_factory=dict)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("name must not be blank")
        return stripped


class StrategyRule(StrictSchema):
    type: str = Field(min_length=1)
    description: str = Field(min_length=1)
    parameters: dict[str, Any] = Field(default_factory=dict)

    @field_validator("type", "description")
    @classmethod
    def reject_blank_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("must not be blank")
        return stripped


class SourceQuote(StrictSchema):
    transcript_id: int = Field(gt=0)
    quote: str = Field(min_length=1)
    start_seconds: float | None = Field(default=None, ge=0)

    @field_validator("quote")
    @classmethod
    def reject_blank_quote(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("quote must not be blank")
        return stripped


class StrategySpec(StrictSchema):
    name: str = Field(min_length=1)
    description: str = Field(min_length=1)
    market: str = Field(min_length=1)
    symbols: list[str] = Field(min_length=1)
    timeframe: str = Field(min_length=1)
    side: Literal["long", "short", "both"] = "long"
    indicators: list[IndicatorSpec] = Field(default_factory=list)
    entry_rules: list[StrategyRule] = Field(min_length=1)
    exit_rules: list[StrategyRule] = Field(min_length=1)
    risk_rules: list[StrategyRule] = Field(min_length=1)
    invalidations: list[str] = Field(default_factory=list)
    source_quotes: list[SourceQuote] = Field(min_length=1)

    @field_validator("name", "description", "market", "timeframe")
    @classmethod
    def reject_blank_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("must not be blank")
        return stripped

    @field_validator("symbols")
    @classmethod
    def normalize_symbols(cls, values: list[str]) -> list[str]:
        symbols = [value.strip().upper() for value in values if value.strip()]
        if not symbols:
            raise ValueError("at least one symbol is required")
        return symbols

    @field_validator("invalidations")
    @classmethod
    def remove_blank_invalidations(cls, values: list[str]) -> list[str]:
        return [value.strip() for value in values if value.strip()]
