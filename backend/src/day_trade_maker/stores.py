from __future__ import annotations

from datetime import UTC, datetime

from day_trade_maker.backtest import BacktestResult
from day_trade_maker.market_data import Candle
from day_trade_maker.persistence import SQLiteAuditSnapshotRepository
from day_trade_maker.schemas import (
    AuditSnapshot,
    BacktestRun,
    BrokerOrderSubmissionCapability,
    MarketDataDataset,
    PaperOrderIntent,
    PaperOrderIntentCreate,
    RiskCheckRun,
    StrategyCandidate,
    Transcript,
    TranscriptCreate,
)
from day_trade_maker.strategy_spec import StrategySpec


class TranscriptStore:
    def __init__(self, transcripts: list[Transcript] | None = None) -> None:
        self._transcripts: list[Transcript] = list(transcripts or [])
        self._next_id = next_id(self._transcripts)

    def create(self, transcript: TranscriptCreate) -> Transcript:
        saved = Transcript(id=self._next_id, **transcript.model_dump())
        self._next_id += 1
        self._transcripts.append(saved)
        persist_all()
        return saved

    def get(self, transcript_id: int) -> Transcript | None:
        return next(
            (transcript for transcript in self._transcripts if transcript.id == transcript_id),
            None,
        )

    def list(self) -> list[Transcript]:
        return list(self._transcripts)

    def replace_all(self, transcripts: list[Transcript]) -> None:
        self._transcripts = list(transcripts)
        self._next_id = next_id(transcripts)
        persist_all()


class StrategyCandidateStore:
    def __init__(self, strategies: list[StrategyCandidate] | None = None) -> None:
        self._strategies: list[StrategyCandidate] = list(strategies or [])
        self._next_id = next_id(self._strategies)

    def create(self, transcript_id: int, spec: StrategySpec) -> StrategyCandidate:
        saved = StrategyCandidate(id=self._next_id, transcript_id=transcript_id, spec=spec)
        self._next_id += 1
        self._strategies.append(saved)
        persist_all()
        return saved

    def list(self) -> list[StrategyCandidate]:
        return list(self._strategies)

    def get(self, strategy_id: int) -> StrategyCandidate | None:
        return next((strategy for strategy in self._strategies if strategy.id == strategy_id), None)

    def approve(self, strategy_id: int, approved_by: str, notes: str) -> StrategyCandidate | None:
        strategy = self.get(strategy_id)
        if strategy is None:
            return None

        approved = strategy.model_copy(
            update={
                "status": "approved",
                "approved_by": approved_by,
                "approval_notes": notes,
                "approved_at": datetime.now(UTC),
            }
        )
        self._strategies = [
            approved if item.id == strategy_id else item for item in self._strategies
        ]
        persist_all()
        return approved

    def replace_all(self, strategies: list[StrategyCandidate]) -> None:
        self._strategies = list(strategies)
        self._next_id = next_id(strategies)
        persist_all()


class MarketDataStore:
    def __init__(self, datasets: list[MarketDataDataset] | None = None) -> None:
        self._datasets: list[MarketDataDataset] = list(datasets or [])
        self._next_id = next_id(self._datasets)

    def create(self, symbol: str, timeframe: str, candles: list[Candle]) -> MarketDataDataset:
        saved = MarketDataDataset(
            id=self._next_id,
            symbol=symbol,
            timeframe=timeframe,
            candles=candles,
        )
        self._next_id += 1
        self._datasets.append(saved)
        persist_all()
        return saved

    def get(self, dataset_id: int) -> MarketDataDataset | None:
        return next((dataset for dataset in self._datasets if dataset.id == dataset_id), None)

    def list(self) -> list[MarketDataDataset]:
        return list(self._datasets)

    def replace_all(self, datasets: list[MarketDataDataset]) -> None:
        self._datasets = list(datasets)
        self._next_id = next_id(datasets)
        persist_all()


class BacktestStore:
    def __init__(self, backtests: list[BacktestRun] | None = None) -> None:
        self._backtests: list[BacktestRun] = list(backtests or [])
        self._next_id = next_id(self._backtests)

    def create(self, strategy_id: int, dataset_id: int, result: BacktestResult) -> BacktestRun:
        saved = BacktestRun(
            id=self._next_id,
            strategy_id=strategy_id,
            dataset_id=dataset_id,
            result=result,
        )
        self._next_id += 1
        self._backtests.append(saved)
        persist_all()
        return saved

    def get(self, backtest_id: int) -> BacktestRun | None:
        return next((backtest for backtest in self._backtests if backtest.id == backtest_id), None)

    def list(self) -> list[BacktestRun]:
        return list(self._backtests)

    def replace_all(self, backtests: list[BacktestRun]) -> None:
        self._backtests = list(backtests)
        self._next_id = next_id(backtests)
        persist_all()


class RiskCheckStore:
    def __init__(self, risk_checks: list[RiskCheckRun] | None = None) -> None:
        self._risk_checks: list[RiskCheckRun] = list(risk_checks or [])
        self._next_id = next_id(self._risk_checks)

    def create(
        self,
        strategy_id: int,
        backtest_id: int,
        paper_mode: bool,
        max_risk_percent: float,
        checks: list[str],
        failures: list[str],
    ) -> RiskCheckRun:
        saved = RiskCheckRun(
            id=self._next_id,
            strategy_id=strategy_id,
            backtest_id=backtest_id,
            paper_mode=paper_mode,
            max_risk_percent=max_risk_percent,
            status="failed" if failures else "passed",
            checks=checks,
            failures=failures,
        )
        self._next_id += 1
        self._risk_checks.append(saved)
        persist_all()
        return saved

    def get(self, risk_check_id: int) -> RiskCheckRun | None:
        return next(
            (risk_check for risk_check in self._risk_checks if risk_check.id == risk_check_id),
            None,
        )

    def list(self) -> list[RiskCheckRun]:
        return list(self._risk_checks)

    def replace_all(self, risk_checks: list[RiskCheckRun]) -> None:
        self._risk_checks = list(risk_checks)
        self._next_id = next_id(risk_checks)
        persist_all()


class PaperOrderIntentStore:
    def __init__(self, order_intents: list[PaperOrderIntent] | None = None) -> None:
        self._order_intents: list[PaperOrderIntent] = list(order_intents or [])
        self._next_id = next_id(self._order_intents)

    def create(
        self,
        payload: PaperOrderIntentCreate,
        checks: list[str],
        order_submission_capability: BrokerOrderSubmissionCapability,
    ) -> PaperOrderIntent:
        saved = PaperOrderIntent(
            id=self._next_id,
            **payload.model_dump(),
            current_execution_mode=order_submission_capability.current_execution_mode,
            paper_broker_submission_implemented=(
                order_submission_capability.paper_broker_submission_implemented
            ),
            paper_broker_submission_enabled=(
                order_submission_capability.paper_broker_submission_enabled
            ),
            live_broker_submission_implemented=(
                order_submission_capability.live_broker_submission_implemented
            ),
            live_broker_submission_enabled=order_submission_capability.live_broker_submission_enabled,
            broker_order_operation_available=(
                order_submission_capability.broker_order_operation_available
            ),
            broker_submission_capability_message=order_submission_capability.message,
            checks=checks,
            message="Paper order intent recorded for audit only; no IBKR order was submitted.",
        )
        self._next_id += 1
        self._order_intents.append(saved)
        persist_all()
        return saved

    def list(self) -> list[PaperOrderIntent]:
        return list(self._order_intents)

    def replace_all(self, order_intents: list[PaperOrderIntent]) -> None:
        self._order_intents = list(order_intents)
        self._next_id = next_id(order_intents)
        persist_all()


def next_id(items: list[object]) -> int:
    return max((item.id for item in items), default=0) + 1


audit_snapshot_repository = SQLiteAuditSnapshotRepository()
_initial_snapshot = audit_snapshot_repository.load()

transcript_store = TranscriptStore(_initial_snapshot.transcripts)
strategy_candidate_store = StrategyCandidateStore(_initial_snapshot.strategies)
market_data_store = MarketDataStore(_initial_snapshot.market_data)
backtest_store = BacktestStore(_initial_snapshot.backtests)
risk_check_store = RiskCheckStore(_initial_snapshot.risk_checks)
paper_order_intent_store = PaperOrderIntentStore(_initial_snapshot.paper_order_intents)


def current_snapshot() -> AuditSnapshot:
    return AuditSnapshot(
        transcripts=transcript_store.list(),
        strategies=strategy_candidate_store.list(),
        market_data=market_data_store.list(),
        backtests=backtest_store.list(),
        risk_checks=risk_check_store.list(),
        paper_order_intents=paper_order_intent_store.list(),
    )


def reset_all_audit_state() -> AuditSnapshot:
    transcript_store._transcripts = []
    transcript_store._next_id = 1
    strategy_candidate_store._strategies = []
    strategy_candidate_store._next_id = 1
    market_data_store._datasets = []
    market_data_store._next_id = 1
    backtest_store._backtests = []
    backtest_store._next_id = 1
    risk_check_store._risk_checks = []
    risk_check_store._next_id = 1
    paper_order_intent_store._order_intents = []
    paper_order_intent_store._next_id = 1
    empty_snapshot = current_snapshot()
    audit_snapshot_repository.save(empty_snapshot)
    return empty_snapshot


def persist_all() -> None:
    if "audit_snapshot_repository" in globals():
        audit_snapshot_repository.save(current_snapshot())
