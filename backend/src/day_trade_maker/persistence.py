from __future__ import annotations

import os
import sqlite3
from pathlib import Path

from day_trade_maker.schemas import AuditSnapshot


class SQLiteAuditSnapshotRepository:
    def __init__(self, db_path: Path | str | None = None) -> None:
        self.db_path = Path(db_path or default_audit_db_path())

    def load(self) -> AuditSnapshot:
        if not self.db_path.exists():
            return AuditSnapshot()

        with sqlite3.connect(self.db_path) as connection:
            ensure_schema(connection)
            row = connection.execute(
                "SELECT payload FROM audit_snapshots WHERE id = 1",
            ).fetchone()

        if row is None:
            return AuditSnapshot()

        return AuditSnapshot.model_validate_json(row[0])

    def save(self, snapshot: AuditSnapshot) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.db_path) as connection:
            ensure_schema(connection)
            connection.execute(
                """
                INSERT INTO audit_snapshots (id, payload)
                VALUES (1, ?)
                ON CONFLICT(id) DO UPDATE SET payload = excluded.payload
                """,
                (snapshot.model_dump_json(),),
            )
            connection.commit()


def ensure_schema(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS audit_snapshots (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            payload TEXT NOT NULL
        )
        """
    )


def default_audit_db_path() -> Path:
    configured = os.environ.get("DAY_TRADE_MAKER_AUDIT_DB_PATH")
    if configured:
        return Path(configured)
    return Path.cwd() / ".day-trade-maker" / "audit.sqlite3"
