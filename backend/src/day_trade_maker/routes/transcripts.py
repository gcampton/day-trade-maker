from fastapi import APIRouter, status

from day_trade_maker.schemas import Transcript, TranscriptCreate
from day_trade_maker.stores import transcript_store

router = APIRouter(prefix="/api/transcripts", tags=["transcripts"])


@router.post("", response_model=Transcript, status_code=status.HTTP_201_CREATED)
def create_transcript(transcript: TranscriptCreate) -> Transcript:
    return transcript_store.create(transcript)


@router.get("", response_model=list[Transcript])
def list_transcripts() -> list[Transcript]:
    return transcript_store.list()
