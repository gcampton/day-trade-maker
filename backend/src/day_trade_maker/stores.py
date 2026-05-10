from day_trade_maker.backtest import BacktestResult
from day_trade_maker.market_data import Candle
from day_trade_maker.schemas import (
    BacktestRun,
    MarketDataDataset,
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


transcript_store = TranscriptStore()
strategy_candidate_store = StrategyCandidateStore()
market_data_store = MarketDataStore()
backtest_store = BacktestStore()
