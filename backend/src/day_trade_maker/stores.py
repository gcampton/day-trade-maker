from day_trade_maker.schemas import StrategyCandidate, Transcript, TranscriptCreate
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


transcript_store = TranscriptStore()
strategy_candidate_store = StrategyCandidateStore()
