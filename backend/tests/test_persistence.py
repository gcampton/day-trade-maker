from pathlib import Path

from day_trade_maker.persistence import SQLiteAuditSnapshotRepository
from day_trade_maker.schemas import AuditSnapshot, PaperBrokerOrderSubmission, Transcript


def test_sqlite_repository_restores_audit_snapshot_after_new_instance(tmp_path: Path) -> None:
    db_path = tmp_path / "audit.sqlite3"
    repository = SQLiteAuditSnapshotRepository(db_path)
    snapshot = AuditSnapshot(
        transcripts=[
            Transcript(
                id=7,
                title="Persisted transcript",
                source_url=None,
                creator="Example Trader",
                raw_text="Risk one percent on the opening range breakout.",
                symbols=["AAPL"],
                timeframes=["5m"],
            )
        ],
        paper_broker_order_submissions=[
            PaperBrokerOrderSubmission(
                id=9,
                order_intent_id=4,
                broker_order_id="12345",
                broker_response={"broker_order_id": "12345", "status": "Submitted"},
                checks=["paper broker submission enabled"],
                message="IBKR paper order submitted; live trading remains disabled.",
            )
        ],
    )

    repository.save(snapshot)
    restored = SQLiteAuditSnapshotRepository(db_path).load()

    assert restored.transcripts[0].id == 7
    assert restored.transcripts[0].title == "Persisted transcript"
    assert restored.paper_broker_order_submissions[0].id == 9
    assert restored.paper_broker_order_submissions[0].broker_order_id == "12345"


def test_sqlite_repository_returns_empty_snapshot_before_first_save(tmp_path: Path) -> None:
    restored = SQLiteAuditSnapshotRepository(tmp_path / "missing.sqlite3").load()

    assert restored.version == 1
    assert restored.transcripts == []
    assert restored.paper_order_intents == []
    assert restored.paper_broker_order_submissions == []
