from datetime import UTC, datetime

from day_trade_maker.backtest import BacktestResult
from day_trade_maker.market_data import Candle
from day_trade_maker.schemas import (
    BacktestRun,
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
    def __init__(self) -> None:
        self._transcripts: list[Transcript] = []
        self._next_id = 1

    def create(self, transcript: TranscriptCreate) -> Transcript:
        saved = Transcript(id=self._next_id, **transcript.model_dump())
        self._next_id += 1
        self._transcripts.append(saved)
        return saved

    def get(self, transcript_id: int) -> Transcript | None:
        return next(
            (transcript for transcript in self._transcripts if transcript.id == transcript_id),
            None,
        )

    def list(self) -> list[Transcript]:
        return list(self._transcripts)


class StrategyCandidateStore:
    def __init__(self) -> None:
        self._strategies: list[StrategyCandidate] = []
        self._next_id = 1

    def create(self, transcript_id: int, spec: StrategySpec) -> StrategyCandidate:
        saved = StrategyCandidate(id=self._next_id, transcript_id=transcript_id, spec=spec)
        self._next_id += 1
        self._strategies.append(saved)
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
        return approved


class MarketDataStore:
    def __init__(self) -> None:
        self._datasets: list[MarketDataDataset] = []
        self._next_id = 1

    def create(self, symbol: str, timeframe: str, candles: list[Candle]) -> MarketDataDataset:
        saved = MarketDataDataset(
            id=self._next_id,
            symbol=symbol,
            timeframe=timeframe,
            candles=candles,
        )
        self._next_id += 1
        self._datasets.append(saved)
        return saved

    def get(self, dataset_id: int) -> MarketDataDataset | None:
        return next((dataset for dataset in self._datasets if dataset.id == dataset_id), None)


class BacktestStore:
    def __init__(self) -> None:
        self._backtests: list[BacktestRun] = []
        self._next_id = 1

    def create(self, strategy_id: int, dataset_id: int, result: BacktestResult) -> BacktestRun:
        saved = BacktestRun(
            id=self._next_id,
            strategy_id=strategy_id,
            dataset_id=dataset_id,
            result=result,
        )
        self._next_id += 1
        self._backtests.append(saved)
        return saved

    def get(self, backtest_id: int) -> BacktestRun | None:
        return next((backtest for backtest in self._backtests if backtest.id == backtest_id), None)


class RiskCheckStore:
    def __init__(self) -> None:
        self._risk_checks: list[RiskCheckRun] = []
        self._next_id = 1

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
        return saved

    def get(self, risk_check_id: int) -> RiskCheckRun | None:
        return next(
            (risk_check for risk_check in self._risk_checks if risk_check.id == risk_check_id),
            None,
        )


class PaperOrderIntentStore:
    def __init__(self) -> None:
        self._order_intents: list[PaperOrderIntent] = []
        self._next_id = 1

    def create(self, payload: PaperOrderIntentCreate, checks: list[str]) -> PaperOrderIntent:
        saved = PaperOrderIntent(
            id=self._next_id,
            **payload.model_dump(),
            checks=checks,
            message="Paper order intent recorded for audit only; no IBKR order was submitted.",
        )
        self._next_id += 1
        self._order_intents.append(saved)
        return saved


transcript_store = TranscriptStore()
strategy_candidate_store = StrategyCandidateStore()
market_data_store = MarketDataStore()
backtest_store = BacktestStore()
risk_check_store = RiskCheckStore()
paper_order_intent_store = PaperOrderIntentStore()
