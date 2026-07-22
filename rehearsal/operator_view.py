from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from datetime import UTC, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from rehearsal.common import canonical_bytes, digest

FIELDS = [
    "projection_contract_version", "projection_id", "generated_at", "candidate_id",
    "event_contract_version", "source_event_id", "event_type", "event_timestamp",
    "session_pseudonym", "activity_pseudonym", "state", "confidence_band",
    "conformal_disposition", "continuity", "receiver_commit_ref", "delivery_status",
    "evidence_refs",
]


def _pseudonym(value: str, domain: str) -> str:
    return hashlib.sha256(f"v0317:{domain}:{value}".encode()).hexdigest()


def project(event: dict, commit_id: str, generated_at: str) -> dict:
    payload = event.get("payload", {})
    prediction = event.get("prediction_ref", {})
    value = {
        "projection_contract_version": "operator_projection_v1",
        "projection_id": "opr_" + digest([event["event_id"], commit_id]),
        "generated_at": generated_at,
        "candidate_id": event["candidate_ref"]["candidate_id"],
        "event_contract_version": event["event_contract_version"],
        "source_event_id": event["event_id"],
        "event_type": event["event_type"],
        "event_timestamp": event["event_timestamp"],
        "session_pseudonym": _pseudonym(event["runtime_ref"]["session_id"], "session"),
        "activity_pseudonym": _pseudonym(event["activity_key"], "activity"),
        "state": payload.get("state"),
        "confidence_band": payload.get("reason_code", "frozen_observation"),
        "conformal_disposition": "frozen_candidate_output",
        "continuity": {"causal_order": event["causal_order"], "previous": event["runtime_ref"]["hash_chain_previous"]},
        "receiver_commit_ref": commit_id,
        "delivery_status": "durable",
        "evidence_refs": [prediction.get("prediction_id"), prediction.get("source_capture_id")],
    }
    if list(value) != FIELDS:
        raise RuntimeError("operator_projection_field_mismatch")
    return value


class ReadOnlyStore:
    def __init__(self, path: Path) -> None:
        self.path = path

    def rows(self, after: int, limit: int) -> list[dict]:
        if not self.path.is_file():
            return []
        db = sqlite3.connect(f"file:{self.path.as_posix()}?mode=ro", uri=True, timeout=2)
        try:
            result = db.execute(
                "SELECT rowid,canonical_event,commit_id FROM receiver_events WHERE rowid>? ORDER BY rowid LIMIT ?",
                (after, min(max(limit, 1), 1000)),
            ).fetchall()
        finally:
            db.close()
        generated = datetime.now(UTC).isoformat()
        return [{"cursor": rowid, "projection": project(json.loads(body), commit_id, generated)} for rowid, body, commit_id in result]


def serve(host: str, port: int, store: ReadOnlyStore) -> None:
    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def _reply(self, status: int, value: object, head: bool = False) -> None:
            body = canonical_bytes(value)
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store, immutable")
            self.send_header("Allow", "GET, HEAD")
            self.end_headers()
            if not head:
                self.wfile.write(body)

        def _get(self, head: bool = False) -> None:
            parsed = urlparse(self.path)
            if parsed.path in {"/health", "/ready"}:
                ready = store.path.is_file()
                self._reply(200 if ready else 503, {"status": "ready" if ready else "unavailable", "read_only": True}, head)
                return
            if parsed.path != "/operator/v1/projections":
                self._reply(404, {"error_code": "not_found"}, head)
                return
            query = parse_qs(parsed.query)
            try:
                after = int(query.get("after", ["0"])[0])
                limit = int(query.get("limit", ["100"])[0])
            except ValueError:
                self._reply(400, {"error_code": "invalid_cursor"}, head)
                return
            rows = store.rows(after, limit)
            self._reply(200, {"projection_contract_version": "operator_projection_v1", "read_only": True, "rows": rows}, head)

        def do_GET(self) -> None:
            self._get(False)

        def do_HEAD(self) -> None:
            self._get(True)

        def _reject_write(self) -> None:
            self._reply(405, {"error_code": "read_only", "allowed_methods": ["GET", "HEAD"]})

        do_POST = _reject_write
        do_PUT = _reject_write
        do_DELETE = _reject_write
        do_PATCH = _reject_write

        def log_message(self, fmt: str, *args: object) -> None:
            return

    ThreadingHTTPServer((host, port), Handler).serve_forever()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=7080)
    parser.add_argument("--receiver-db", type=Path, default=Path("/run/receiver/receiver.sqlite"))
    args = parser.parse_args()
    serve(args.host, args.port, ReadOnlyStore(args.receiver_db))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

