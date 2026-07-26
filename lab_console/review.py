from __future__ import annotations

import json
import uuid
from typing import Any

from .database import Database, now
from .integrity import semantic_sha

ALLOWED_STATUS = {"not_started", "in_review", "needs_additional_evidence", "reviewed_without_determination", "closed_as_laboratory_example"}


class ReviewService:
    def __init__(self, db: Database) -> None:
        self.db = db

    def create(self, card_id: str, source_sha256: str) -> dict[str, Any]:
        stamp = now()
        payload = {"schema_version": "manual_review_session_v1", "review_session_id": "review_" + uuid.uuid4().hex,
                   "source_card_id": card_id, "source_bundle_sha256": source_sha256, "started_at": stamp,
                   "updated_at": stamp, "status": "in_review", "checklist": [], "notes": [],
                   "reviewed_hypothesis_ids": [], "reviewed_gap_ids": [], "reviewed_question_ids": [],
                   "unresolved_items": [], "decision": None, "reviewer_role": "laboratory_admin", "audit_event_ids": []}
        with self.db.connect() as con:
            con.execute("INSERT INTO reviews VALUES(?,?,?,?,?,?,?)", (payload["review_session_id"], card_id, source_sha256,
                        payload["status"], json.dumps(payload, ensure_ascii=False), stamp, stamp))
        event = self.db.audit("review_created", payload["review_session_id"], "success")
        payload["audit_event_ids"].append(event)
        self._save(payload)
        return payload

    def _save(self, payload: dict[str, Any]) -> None:
        payload["updated_at"] = now()
        with self.db.connect() as con:
            con.execute("UPDATE reviews SET status=?,payload=?,updated_at=? WHERE id=?",
                        (payload["status"], json.dumps(payload, ensure_ascii=False), payload["updated_at"], payload["review_session_id"]))

    def get(self, review_id: str) -> dict[str, Any] | None:
        with self.db.connect() as con:
            row = con.execute("SELECT payload FROM reviews WHERE id=?", (review_id,)).fetchone()
        return json.loads(row[0]) if row else None

    def list(self) -> list[dict[str, Any]]:
        with self.db.connect() as con:
            return [json.loads(r[0]) for r in con.execute("SELECT payload FROM reviews ORDER BY created_at DESC")]

    def add_check(self, review_id: str, item_id: str, checked: bool) -> dict[str, Any]:
        payload = self._required(review_id)
        payload["checklist"].append({"schema_version": "manual_review_check_v1", "check_id": "check_" + uuid.uuid4().hex,
                                     "item_id": item_id, "checked": bool(checked), "checked_at": now()})
        self._save(payload); self.db.audit("review_check_added", review_id, "success")
        return payload

    def add_note(self, review_id: str, text: str) -> dict[str, Any]:
        if not text.strip() or len(text) > 4000 or "<" in text or ">" in text:
            raise ValueError("unsafe_review_note")
        payload = self._required(review_id)
        payload["notes"].append({"schema_version": "manual_review_note_v1", "note_id": "note_" + uuid.uuid4().hex,
                                 "text": text, "created_at": now(), "is_evidence": False})
        self._save(payload); self.db.audit("review_note_added", review_id, "success")
        return payload

    def decide(self, review_id: str, status: str, limitations: list[str], next_manual_step: str) -> dict[str, Any]:
        if status not in ALLOWED_STATUS or status in {"not_started", "in_review"}:
            raise ValueError("forbidden_review_status")
        payload = self._required(review_id)
        payload["status"] = status
        payload["decision"] = {"schema_version": "manual_review_decision_v1", "no_final_determination": True,
                               "no_automatic_action": True, "limitations": limitations, "next_manual_step": next_manual_step}
        self._save(payload); self.db.audit("review_decision_recorded", review_id, "success")
        return payload

    def export(self, review_id: str) -> dict[str, Any]:
        payload = self._required(review_id)
        return {"schema_version": "console_export_bundle_v1", "source_reference": {"card_id": payload["source_card_id"],
                "sha256": payload["source_bundle_sha256"]}, "review_overlay": payload,
                "safety": {"source_artifacts_modified": False, "final_determination": False, "automatic_action": False},
                "semantic_sha256": semantic_sha(payload)}

    def _required(self, review_id: str) -> dict[str, Any]:
        payload = self.get(review_id)
        if not payload:
            raise KeyError("review_not_found")
        return payload
