from fastapi import APIRouter, HTTPException, status

from day_trade_maker.schemas import StrategyApprovalCreate, StrategyCandidate
from day_trade_maker.services.strategy_extraction import extract_strategy_specs
from day_trade_maker.stores import strategy_candidate_store, transcript_store

router = APIRouter(tags=["strategies"])


@router.post(
    "/api/transcripts/{transcript_id}/extract-strategies",
    response_model=list[StrategyCandidate],
    status_code=status.HTTP_201_CREATED,
)
def extract_strategies(transcript_id: int) -> list[StrategyCandidate]:
    transcript = transcript_store.get(transcript_id)
    if transcript is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transcript not found")

    specs = extract_strategy_specs(transcript)
    return [
        strategy_candidate_store.create(transcript_id=transcript.id, spec=spec)
        for spec in specs
    ]


@router.get("/api/strategies", response_model=list[StrategyCandidate])
def list_strategies() -> list[StrategyCandidate]:
    return strategy_candidate_store.list()


@router.post("/api/strategies/{strategy_id}/approve", response_model=StrategyCandidate)
def approve_strategy(strategy_id: int, payload: StrategyApprovalCreate) -> StrategyCandidate:
    strategy = strategy_candidate_store.approve(
        strategy_id=strategy_id,
        approved_by=payload.approved_by,
        notes=payload.notes,
    )
    if strategy is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Strategy not found")
    return strategy
