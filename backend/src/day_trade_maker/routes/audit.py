from fastapi import APIRouter

from day_trade_maker.schemas import AuditImportSummary, AuditPersistenceStatus, AuditSnapshot
from day_trade_maker.stores import (
    audit_snapshot_repository,
    backtest_store,
    market_data_store,
    paper_order_intent_store,
    risk_check_store,
    strategy_candidate_store,
    transcript_store,
)

router = APIRouter(prefix="/api/audit", tags=["audit"])


@router.get("/status", response_model=AuditPersistenceStatus)
def get_audit_persistence_status() -> AuditPersistenceStatus:
    return AuditPersistenceStatus(
        db_path=str(audit_snapshot_repository.db_path),
        snapshot_exists=audit_snapshot_repository.db_path.exists(),
        transcript_count=len(transcript_store.list()),
        strategy_count=len(strategy_candidate_store.list()),
        market_data_count=len(market_data_store.list()),
        backtest_count=len(backtest_store.list()),
        risk_check_count=len(risk_check_store.list()),
        paper_order_intent_count=len(paper_order_intent_store.list()),
    )


@router.get("/export", response_model=AuditSnapshot)
def export_audit_snapshot() -> AuditSnapshot:
    return AuditSnapshot(
        transcripts=transcript_store.list(),
        strategies=strategy_candidate_store.list(),
        market_data=market_data_store.list(),
        backtests=backtest_store.list(),
        risk_checks=risk_check_store.list(),
        paper_order_intents=paper_order_intent_store.list(),
    )


@router.post("/import", response_model=AuditImportSummary)
def import_audit_snapshot(snapshot: AuditSnapshot) -> AuditImportSummary:
    transcript_store.replace_all(snapshot.transcripts)
    strategy_candidate_store.replace_all(snapshot.strategies)
    market_data_store.replace_all(snapshot.market_data)
    backtest_store.replace_all(snapshot.backtests)
    risk_check_store.replace_all(snapshot.risk_checks)
    paper_order_intent_store.replace_all(snapshot.paper_order_intents)

    return AuditImportSummary(
        transcript_count=len(snapshot.transcripts),
        strategy_count=len(snapshot.strategies),
        market_data_count=len(snapshot.market_data),
        backtest_count=len(snapshot.backtests),
        risk_check_count=len(snapshot.risk_checks),
        paper_order_intent_count=len(snapshot.paper_order_intents),
        message="Audit snapshot imported into in-memory stores.",
    )
