from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

MIGRATIONS = (
    """CREATE TABLE IF NOT EXISTS schema_migrations(version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS reviews(id TEXT PRIMARY KEY, card_id TEXT NOT NULL, source_sha256 TEXT NOT NULL, status TEXT NOT NULL, payload TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS task_runs(id TEXT PRIMARY KEY, task_id TEXT NOT NULL, status TEXT NOT NULL, pid INTEGER, exit_code INTEGER, catalog_sha256 TEXT NOT NULL, head TEXT NOT NULL, tree_state TEXT NOT NULL, started_at TEXT NOT NULL, finished_at TEXT, log_path TEXT NOT NULL, error TEXT);
    CREATE TABLE IF NOT EXISTS audit_events(id INTEGER PRIMARY KEY AUTOINCREMENT, occurred_at TEXT NOT NULL, action TEXT NOT NULL, object_id TEXT NOT NULL, outcome TEXT NOT NULL, detail TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS review_versions(id INTEGER PRIMARY KEY AUTOINCREMENT, review_id TEXT NOT NULL, version INTEGER NOT NULL, occurred_at TEXT NOT NULL, action TEXT NOT NULL, payload TEXT NOT NULL, UNIQUE(review_id,version));
    CREATE INDEX IF NOT EXISTS idx_reviews_card_status ON reviews(card_id,status);
    CREATE INDEX IF NOT EXISTS idx_review_versions_review ON review_versions(review_id,version);""" +
    """CREATE TABLE IF NOT EXISTS laboratory_runs(token TEXT PRIMARY KEY, execution_id TEXT NOT NULL UNIQUE, run_semantic_id TEXT NOT NULL, status TEXT NOT NULL, plan_json TEXT NOT NULL, record_json TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS run_comparisons(token TEXT PRIMARY KEY, left_run_token TEXT NOT NULL, right_run_token TEXT NOT NULL, status TEXT NOT NULL, bundle_json TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS comparison_reviews(id TEXT PRIMARY KEY, comparison_token TEXT NOT NULL, version INTEGER NOT NULL, status TEXT NOT NULL, payload TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS comparison_review_versions(id INTEGER PRIMARY KEY AUTOINCREMENT, review_id TEXT NOT NULL, version INTEGER NOT NULL, occurred_at TEXT NOT NULL, action TEXT NOT NULL, payload TEXT NOT NULL, UNIQUE(review_id,version));
    CREATE INDEX IF NOT EXISTS idx_lab_runs_status ON laboratory_runs(status);
    CREATE INDEX IF NOT EXISTS idx_lab_runs_semantic ON laboratory_runs(run_semantic_id);
    CREATE INDEX IF NOT EXISTS idx_run_comparisons_runs ON run_comparisons(left_run_token,right_run_token);
    CREATE INDEX IF NOT EXISTS idx_comparison_reviews_comparison ON comparison_reviews(comparison_token,status);
    CREATE TABLE IF NOT EXISTS candidate_proposals(token TEXT PRIMARY KEY, proposal_id TEXT NOT NULL UNIQUE, status TEXT NOT NULL, payload_json TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS proposal_training_runs(execution_id TEXT PRIMARY KEY, proposal_token TEXT NOT NULL, training_semantic_id TEXT NOT NULL, status TEXT NOT NULL, payload_json TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS candidate_proposal_reviews(id TEXT PRIMARY KEY, proposal_token TEXT NOT NULL, version INTEGER NOT NULL, status TEXT NOT NULL, payload_json TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS candidate_proposal_review_versions(id INTEGER PRIMARY KEY AUTOINCREMENT, review_id TEXT NOT NULL, version INTEGER NOT NULL, occurred_at TEXT NOT NULL, action TEXT NOT NULL, payload_json TEXT NOT NULL, UNIQUE(review_id,version));
    CREATE INDEX IF NOT EXISTS idx_candidate_proposals_status ON candidate_proposals(status);
    CREATE INDEX IF NOT EXISTS idx_proposal_training_runs_proposal ON proposal_training_runs(proposal_token,status);
    CREATE INDEX IF NOT EXISTS idx_candidate_proposal_reviews_proposal ON candidate_proposal_reviews(proposal_token,status);""" +
    """CREATE TABLE IF NOT EXISTS blind_validations(token TEXT PRIMARY KEY, lineage_id TEXT NOT NULL UNIQUE, status TEXT NOT NULL, payload_json TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS blind_validation_reviews(id TEXT PRIMARY KEY, validation_token TEXT NOT NULL, version INTEGER NOT NULL, status TEXT NOT NULL, payload_json TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS blind_validation_review_versions(id INTEGER PRIMARY KEY AUTOINCREMENT, review_id TEXT NOT NULL, version INTEGER NOT NULL, occurred_at TEXT NOT NULL, action TEXT NOT NULL, payload_json TEXT NOT NULL, UNIQUE(review_id,version));
    CREATE INDEX IF NOT EXISTS idx_blind_validations_status ON blind_validations(status);
    CREATE INDEX IF NOT EXISTS idx_blind_reviews_validation ON blind_validation_reviews(validation_token,status);""",
)


def now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


class Database:
    def __init__(self, path: Path) -> None:
        self.path = path

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        con = sqlite3.connect(self.path, timeout=5)
        con.row_factory = sqlite3.Row
        try:
            yield con
            con.commit()
        finally:
            con.close()

    def migrate(self) -> None:
        with self.connect() as con:
            for version, sql in enumerate(MIGRATIONS, 1):
                con.executescript(sql)
                con.execute("INSERT OR IGNORE INTO schema_migrations VALUES(?,?)", (version, now()))

    def audit(self, action: str, object_id: str, outcome: str, detail: dict[str, Any] | None = None) -> int:
        with self.connect() as con:
            cur = con.execute("INSERT INTO audit_events(occurred_at,action,object_id,outcome,detail) VALUES(?,?,?,?,?)",
                              (now(), action, object_id, outcome, json.dumps(detail or {}, ensure_ascii=False, sort_keys=True)))
            return int(cur.lastrowid)

    def audits(self, limit: int = 100) -> list[dict[str, Any]]:
        with self.connect() as con:
            return [dict(row) for row in con.execute("SELECT * FROM audit_events ORDER BY id DESC LIMIT ?", (min(limit, 500),))]
