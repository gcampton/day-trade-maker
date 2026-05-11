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
    configured_host: str
    configured_port: int
    configured_client_id: int
    connection_diagnostic: str
    message: str


class BrokerAccountSnapshot(BaseModel):
    provider: Literal["interactive_brokers"] = "interactive_brokers"
    mode: Literal["paper"] = "paper"
    read_only: bool = True
    order_submission_enabled: bool = False
    account_snapshot_enabled: bool = False
    account_data_loaded: bool = False
    account_reader: Literal["static", "ib_async"] = "static"
    ibkr_client_dependency_available: bool = False
    account_id: str | None = None
    balances: list[dict[str, str | float]] = Field(default_factory=list)
    positions: list[dict[str, str | float]] = Field(default_factory=list)
    message: str


class BrokerConnectivityProbe(BaseModel):
    provider: Literal["interactive_brokers"] = "interactive_brokers"
    probe_status: Literal["unavailable", "not_connected", "connected"] = "unavailable"
    connection_status: Literal["not_connected", "connected"] = "not_connected"
    read_only: bool = True
    order_submission_enabled: bool = False
    probe_enabled: bool = False
    probe_attempted: bool = False
    account_data_loaded: bool = False
    host: str
    port: int
    timeout_seconds: float = 1.0
    message: str


class BrokerCapabilities(BaseModel):
    provider: Literal["interactive_brokers"] = "interactive_brokers"
    current_execution_mode: Literal["audit_only"] = "audit_only"
    supports_order_intents: bool = True
    supports_paper_broker_submission: bool = False
    supports_live_broker_submission: bool = False
    order_submission_enabled: bool = False
    message: str


class BrokerOrderSubmissionCapability(BaseModel):
    provider: Literal["interactive_brokers"] = "interactive_brokers"
    current_execution_mode: Literal["audit_only"] = "audit_only"
    order_intents_supported: bool = True
    paper_broker_submission_implemented: bool = False
    paper_broker_submission_enabled: bool = False
    live_broker_submission_implemented: bool = False
    live_broker_submission_enabled: bool = False
    broker_order_operation_available: bool = False
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
    current_execution_mode: Literal["audit_only"] = "audit_only"
    paper_broker_submission_implemented: bool = False
    paper_broker_submission_enabled: bool = False
    live_broker_submission_implemented: bool = False
    live_broker_submission_enabled: bool = False
    broker_order_operation_available: bool = False
    broker_submission_capability_message: str = (
        "IBKR paper order submission is not implemented or enabled; "
        "this app only records audit-only paper order intents."
    )
    checks: list[str]
    message: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class AuditSnapshot(BaseModel):
    version: Literal[1] = 1
    exported_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    transcripts: list[Transcript] = Field(default_factory=list)
    strategies: list[StrategyCandidate] = Field(default_factory=list)
    market_data: list[MarketDataDataset] = Field(default_factory=list)
    backtests: list[BacktestRun] = Field(default_factory=list)
    risk_checks: list[RiskCheckRun] = Field(default_factory=list)
    paper_order_intents: list[PaperOrderIntent] = Field(default_factory=list)


class AuditImportSummary(BaseModel):
    version: Literal[1] = 1
    transcript_count: int
    strategy_count: int
    market_data_count: int
    backtest_count: int
    risk_check_count: int
    paper_order_intent_count: int
    message: str


class AuditResetRequest(BaseModel):
    confirmation: str

    @field_validator("confirmation")
    @classmethod
    def require_confirmation_phrase(cls, value: str) -> str:
        if value != "RESET LOCAL AUDIT STATE":
            raise ValueError("confirmation must be RESET LOCAL AUDIT STATE")
        return value


class AuditPersistenceStatus(BaseModel):
    provider: Literal["sqlite"] = "sqlite"
    db_path: str
    snapshot_exists: bool
    transcript_count: int
    strategy_count: int
    market_data_count: int
    backtest_count: int
    risk_check_count: int
    paper_order_intent_count: int
