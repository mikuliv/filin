from __future__ import annotations

import sqlite3
from pathlib import Path

from staging.storage import ConnectorJournal, ReceiverStore


def _observability_connection(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path, timeout=5, check_same_thread=False, isolation_level=None)
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("PRAGMA synchronous=OFF")
    db.execute("PRAGMA busy_timeout=5000")
    db.execute(
        "CREATE TABLE IF NOT EXISTS trace("
        "event_id TEXT NOT NULL,"
        "field TEXT NOT NULL,"
        "monotonic_ns INTEGER NOT NULL,"
        "PRIMARY KEY(event_id,field)"
        ")"
    )
    return db


class RehearsalConnectorJournal(ConnectorJournal):
    def __init__(self, path: Path, trace_path: Path | None = None) -> None:
        super().__init__(path)
        self.trace_db.close()
        self.trace_path = trace_path or path.with_name("connector-trace.sqlite")
        self.trace_db = _observability_connection(self.trace_path)
        self.db.execute(
            "CREATE INDEX IF NOT EXISTS idx_journal_pending_order "
            "ON journal_events(delivery_status,journal_durable_ns,event_id)"
        )


class RehearsalReceiverStore(ReceiverStore):
    def __init__(self, path: Path, instance_id: str, trace_path: Path | None = None) -> None:
        super().__init__(path, instance_id)
        self.trace_db.close()
        self.trace_path = trace_path or path.with_name("receiver-trace.sqlite")
        self.trace_db = _observability_connection(self.trace_path)
