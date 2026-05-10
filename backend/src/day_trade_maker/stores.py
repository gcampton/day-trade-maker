from day_trade_maker.market_data import Candle
from day_trade_maker.schemas import (
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


transcript_store = TranscriptStore()
strategy_candidate_store = StrategyCandidateStore()
market_data_store = MarketDataStore()
