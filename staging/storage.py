from __future__ import annotations

import json
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any

from staging.contracts import ContractError, canonical_bytes, digest
from staging.contracts.models import REGISTRY_COMMITMENT


def _connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path, timeout=5, check_same_thread=False, isolation_level=None)
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("PRAGMA synchronous=FULL")
    db.execute("PRAGMA foreign_keys=ON")
    db.execute("PRAGMA busy_timeout=5000")
    return db


def _trace_connect(path: Path) -> sqlite3.Connection:
    db = sqlite3.connect(path, timeout=5, check_same_thread=False, isolation_level=None)
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("PRAGMA synchronous=OFF")
    db.execute("PRAGMA busy_timeout=5000")
    return db


class ConnectorJournal:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.db = _connect(path)
        self.lock = threading.RLock()
        self.db.executescript("""
        CREATE TABLE IF NOT EXISTS journal_commits(commit_id TEXT PRIMARY KEY, commit_sha256 TEXT NOT NULL, request_id TEXT UNIQUE NOT NULL, committed_ns INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS journal_events(event_id TEXT PRIMARY KEY, idempotency_key TEXT UNIQUE NOT NULL, event_sha256 TEXT NOT NULL, canonical_event BLOB NOT NULL, candidate_id TEXT NOT NULL, source_sequence INTEGER NOT NULL, ingress_request_id TEXT NOT NULL, commit_id TEXT NOT NULL REFERENCES journal_commits(commit_id), delivery_status TEXT NOT NULL DEFAULT 'pending', attempt_count INTEGER NOT NULL DEFAULT 0, batch_id TEXT, receiver_commit_id TEXT, receiver_commit_sha256 TEXT, receiver_ack_sha256 TEXT, journal_durable_ns INTEGER NOT NULL, checkpoint_ns INTEGER);
        CREATE TABLE IF NOT EXISTS checkpoints(batch_id TEXT PRIMARY KEY, receiver_commit_id TEXT NOT NULL, receiver_commit_sha256 TEXT NOT NULL, receiver_ack_sha256 TEXT NOT NULL, committed_ns INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS trace(event_id TEXT NOT NULL, field TEXT NOT NULL, monotonic_ns INTEGER NOT NULL, PRIMARY KEY(event_id,field));
        """)
        self.trace_db = _trace_connect(path)

    def append(self, request_id: str, events: list[dict[str, Any]]) -> dict[str, Any]:
        accepted, duplicates = [], []
        now = time.monotonic_ns()
        rows = [(event["event_id"], event["idempotency_key"], digest(event), canonical_bytes(event), event["candidate_ref"]["candidate_id"], event["runtime_ref"]["source_sequence"]) for event in events]
        commit_sha = digest([request_id, [[r[0], r[2]] for r in rows], now])
        commit_id = "cjc_" + commit_sha[:32]
        with self.lock:
            self.db.execute("BEGIN IMMEDIATE")
            try:
                existing_request = self.db.execute("SELECT commit_id,commit_sha256 FROM journal_commits WHERE request_id=?", (request_id,)).fetchone()
                if existing_request:
                    known = [row[0] for row in self.db.execute("SELECT event_id FROM journal_events WHERE ingress_request_id=?", (request_id,))]
                    self.db.execute("COMMIT")
                    return {"commit_id": existing_request[0], "commit_sha256": existing_request[1], "accepted": [], "duplicates": known, "committed_ns": now}
                self.db.execute("INSERT INTO journal_commits VALUES(?,?,?,?)", (commit_id, commit_sha, request_id, now))
                for event_id, key, event_sha, body, candidate, sequence in rows:
                    existing = self.db.execute("SELECT event_sha256,idempotency_key FROM journal_events WHERE event_id=? OR idempotency_key=?", (event_id, key)).fetchone()
                    if existing:
                        if existing != (event_sha, key):
                            raise ContractError("idempotency_collision", event_id)
                        duplicates.append(event_id)
                    else:
                        self.db.execute("INSERT INTO journal_events(event_id,idempotency_key,event_sha256,canonical_event,candidate_id,source_sequence,ingress_request_id,commit_id,journal_durable_ns) VALUES(?,?,?,?,?,?,?,?,?)", (event_id, key, event_sha, body, candidate, sequence, request_id, commit_id, now))
                        accepted.append(event_id)
                self.db.execute("COMMIT")
            except Exception:
                self.db.execute("ROLLBACK")
                raise
        return {"commit_id": commit_id, "commit_sha256": commit_sha, "accepted": accepted, "duplicates": duplicates, "committed_ns": now}

    def pending(self, limit: int = 50) -> list[dict[str, Any]]:
        with self.lock:
            rows = self.db.execute("SELECT canonical_event FROM journal_events WHERE delivery_status='pending' ORDER BY journal_durable_ns,event_id LIMIT ?", (limit,)).fetchall()
        return [json.loads(row[0]) for row in rows]

    def trace(self, events: list[dict[str, Any]], field: str, timestamp: int | None = None) -> int:
        value = timestamp or time.monotonic_ns()
        with self.lock:
            self.trace_db.execute("BEGIN IMMEDIATE")
            try:
                self.trace_db.executemany("INSERT OR REPLACE INTO trace VALUES(?,?,?)", [(event["event_id"], field, value) for event in events])
                self.trace_db.execute("COMMIT")
            except Exception:
                self.trace_db.execute("ROLLBACK")
                raise
        return value

    def checkpoint(self, batch: dict[str, Any], ack: dict[str, Any]) -> int:
        now = time.monotonic_ns()
        with self.lock:
            self.db.execute("BEGIN IMMEDIATE")
            try:
                self.db.execute("INSERT OR IGNORE INTO checkpoints VALUES(?,?,?,?,?)", (batch["batch_id"], ack["receiver_commit_id"], ack["receiver_commit_sha256"], ack["ack_sha256"], now))
                for result in ack["event_results"]:
                    if result["status"] in {"accepted", "duplicate"}:
                        self.db.execute("UPDATE journal_events SET delivery_status='acknowledged',attempt_count=attempt_count+1,batch_id=?,receiver_commit_id=?,receiver_commit_sha256=?,receiver_ack_sha256=?,checkpoint_ns=? WHERE event_id=?", (batch["batch_id"], ack["receiver_commit_id"], ack["receiver_commit_sha256"], ack["ack_sha256"], now, result["event_id"]))
                self.db.execute("COMMIT")
            except Exception:
                self.db.execute("ROLLBACK")
                raise
        return now

    def counts(self) -> dict[str, int]:
        with self.lock:
            total = self.db.execute("SELECT count(*) FROM journal_events").fetchone()[0]
            pending = self.db.execute("SELECT count(*) FROM journal_events WHERE delivery_status='pending'").fetchone()[0]
        return {"durable": total, "pending": pending, "acknowledged": total - pending}


class ReceiverStore:
    def __init__(self, path: Path, instance_id: str) -> None:
        self.path, self.instance_id = path, instance_id
        self.db = _connect(path)
        self.lock = threading.RLock()
        self.db.executescript("""
        CREATE TABLE IF NOT EXISTS registry_snapshots(commitment_sha256 TEXT PRIMARY KEY, created_ns INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS batches(batch_id TEXT PRIMARY KEY, attempt_id TEXT NOT NULL, body_sha256 TEXT NOT NULL, received_ns INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS receiver_commits(commit_id TEXT PRIMARY KEY, commit_sha256 TEXT NOT NULL, batch_id TEXT UNIQUE NOT NULL REFERENCES batches(batch_id), committed_ns INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS receiver_events(event_id TEXT PRIMARY KEY, idempotency_key TEXT UNIQUE NOT NULL, event_sha256 TEXT NOT NULL, canonical_event BLOB NOT NULL, batch_id TEXT NOT NULL REFERENCES batches(batch_id), commit_id TEXT NOT NULL, committed_ns INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS acks(batch_id TEXT PRIMARY KEY, ack_sha256 TEXT NOT NULL, canonical_ack BLOB NOT NULL, created_ns INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS rejections(rejection_id INTEGER PRIMARY KEY, batch_id TEXT, event_id TEXT, error_code TEXT NOT NULL, created_ns INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS trace(event_id TEXT NOT NULL, field TEXT NOT NULL, monotonic_ns INTEGER NOT NULL, PRIMARY KEY(event_id,field));
        """)
        self.trace_db = _trace_connect(path)
        self.db.execute("INSERT OR IGNORE INTO registry_snapshots VALUES(?,?)", (REGISTRY_COMMITMENT, time.monotonic_ns()))

    def commit(self, batch: dict[str, Any]) -> dict[str, Any]:
        now = time.monotonic_ns()
        body_sha = digest(batch)
        commit_sha = digest([batch["batch_id"], body_sha, now])
        commit_id = "rrc_" + commit_sha[:32]
        results = []
        with self.lock:
            previous = self.db.execute("SELECT canonical_ack FROM acks WHERE batch_id=?", (batch["batch_id"],)).fetchone()
            if previous:
                return json.loads(previous[0])
            self.db.execute("BEGIN IMMEDIATE")
            try:
                self.db.execute("INSERT INTO batches VALUES(?,?,?,?)", (batch["batch_id"], batch["attempt_id"], body_sha, now))
                self.db.execute("INSERT INTO receiver_commits VALUES(?,?,?,?)", (commit_id, commit_sha, batch["batch_id"], now))
                for event in batch["events"]:
                    event_sha = digest(event)
                    existing = self.db.execute("SELECT event_sha256,idempotency_key FROM receiver_events WHERE event_id=? OR idempotency_key=?", (event["event_id"], event["idempotency_key"])).fetchone()
                    if existing:
                        if existing != (event_sha, event["idempotency_key"]):
                            raise ContractError("idempotency_collision", event["event_id"])
                        status = "duplicate"
                    else:
                        self.db.execute("INSERT INTO receiver_events VALUES(?,?,?,?,?,?,?)", (event["event_id"], event["idempotency_key"], event_sha, canonical_bytes(event), batch["batch_id"], commit_id, now))
                        status = "accepted"
                    results.append({"event_id": event["event_id"], "status": status, "error_code": None})
                ack = {"ack_contract_version": "receiver_batch_ack_v1", "batch_id": batch["batch_id"], "attempt_id": batch["attempt_id"], "receiver_instance_id": self.instance_id, "receiver_commit_id": commit_id, "receiver_commit_sha256": commit_sha, "candidate_registry_commitment_sha256": REGISTRY_COMMITMENT, "durable": True, "event_results": results}
                ack["ack_sha256"] = digest(ack)
                self.db.execute("INSERT INTO acks VALUES(?,?,?,?)", (batch["batch_id"], ack["ack_sha256"], canonical_bytes(ack), time.monotonic_ns()))
                self.db.execute("COMMIT")
            except Exception:
                self.db.execute("ROLLBACK")
                raise
        return ack

    def trace(self, events: list[dict[str, Any]], field: str, timestamp: int | None = None) -> int:
        value = timestamp or time.monotonic_ns()
        with self.lock:
            self.trace_db.execute("BEGIN IMMEDIATE")
            try:
                self.trace_db.executemany("INSERT OR REPLACE INTO trace VALUES(?,?,?)", [(event["event_id"], field, value) for event in events])
                self.trace_db.execute("COMMIT")
            except Exception:
                self.trace_db.execute("ROLLBACK")
                raise
        return value

    def count(self) -> int:
        with self.lock:
            return self.db.execute("SELECT count(*) FROM receiver_events").fetchone()[0]
