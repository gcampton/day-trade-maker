from day_trade_maker.schemas import Transcript, TranscriptCreate


class TranscriptStore:
    def __init__(self) -> None:
        self._transcripts: list[Transcript] = []
        self._next_id = 1

    def create(self, transcript: TranscriptCreate) -> Transcript:
        saved = Transcript(id=self._next_id, **transcript.model_dump())
        self._next_id += 1
        self._transcripts.append(saved)
        return saved

    def list(self) -> list[Transcript]:
        return list(self._transcripts)


transcript_store = TranscriptStore()
