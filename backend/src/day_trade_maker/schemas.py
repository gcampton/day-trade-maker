from datetime import UTC, datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

from day_trade_maker.backtest import BacktestResult
from day_trade_maker.market_data import Candle
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
    approved_by: str | None = None
    approval_notes: str | None = None
    approved_at: datetime | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class StrategyApprovalCreate(BaseModel):
    approved_by: NonEmptyString
    notes: NonEmptyString

    @field_validator("approved_by", "notes")
    @classmethod
    def reject_blank_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("must not be blank")
        return stripped


class MarketDataImport(BaseModel):
    symbol: NonEmptyString
    timeframe: NonEmptyString
    csv_text: NonEmptyString

    @field_validator("symbol")
    @classmethod
    def normalize_symbol(cls, value: str) -> str:
        return value.strip().upper()

    @field_validator("timeframe", "csv_text")
    @classmethod
    def reject_blank_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("must not be blank")
        return stripped


class MarketDataDataset(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    symbol: str
    timeframe: str
    candles: list[Candle]
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @property
    def candle_count(self) -> int:
        return len(self.candles)


class MarketDataDatasetSummary(BaseModel):
    id: int
    symbol: str
    timeframe: str
    candle_count: int
    created_at: datetime


class CandleResponse(Candle):
    @field_serializer("timestamp")
    def serialize_timestamp(self, value: datetime) -> str:
        if value.tzinfo is None:
            return value.isoformat()
        return value.isoformat().replace("+00:00", "Z")


class BacktestCreate(BaseModel):
    strategy_id: int = Field(gt=0)
    dataset_id: int = Field(gt=0)
    starting_cash: float = Field(gt=0)


class BacktestRun(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    strategy_id: int
    dataset_id: int
    result: BacktestResult
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class RiskCheckCreate(BaseModel):
    strategy_id: int = Field(gt=0)
    backtest_id: int = Field(gt=0)
    paper_mode: bool
    max_risk_percent: float = Field(gt=0, le=1)


class RiskCheckRun(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    strategy_id: int
    backtest_id: int
    paper_mode: bool
    max_risk_percent: float
    status: Literal["passed", "failed"]
    checks: list[str]
    failures: list[str]
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class BrokerStatus(BaseModel):
    provider: Literal["interactive_brokers"] = "interactive_brokers"
    mode: Literal["paper"] = "paper"
    connection_status: Literal["not_connected", "connected"] = "not_connected"
    read_only: bool = True
    order_submission_enabled: bool = False
    account_id: str | None = None
    net_liquidation: float | None = None
    currency: str = "USD"
    message: str


class BrokerAccountSnapshot(BaseModel):
    provider: Literal["interactive_brokers"] = "interactive_brokers"
    mode: Literal["paper"] = "paper"
    read_only: bool = True
    order_submission_enabled: bool = False
    account_id: str | None = None
    balances: list[dict[str, str | float]] = Field(default_factory=list)
    positions: list[dict[str, str | float]] = Field(default_factory=list)
    message: str


class PaperOrderIntentCreate(BaseModel):
    strategy_id: int = Field(gt=0)
    risk_check_id: int = Field(gt=0)
    symbol: NonEmptyString
    side: Literal["buy", "sell"]
    quantity: int = Field(gt=0)
    order_type: Literal["market", "limit"]
    limit_price: float | None = Field(default=None, gt=0)
    paper_mode: bool
    user_confirmed: bool

    @field_validator("symbol")
    @classmethod
    def normalize_symbol(cls, value: str) -> str:
        return value.strip().upper()


class PaperOrderIntent(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    strategy_id: int
    risk_check_id: int
    symbol: str
    side: Literal["buy", "sell"]
    quantity: int
    order_type: Literal["market", "limit"]
    limit_price: float | None = None
    paper_mode: bool
    user_confirmed: bool
    status: Literal["created_not_submitted"] = "created_not_submitted"
    submitted_to_broker: bool = False
    order_submission_enabled: bool = False
    checks: list[str]
    message: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
