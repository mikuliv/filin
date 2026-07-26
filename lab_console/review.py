from __future__ import annotations

import copy
import json
import uuid
from typing import Any

from .database import Database, now
from .integrity import semantic_sha

ALLOWED_STATUS = {"not_started", "in_review", "needs_additional_evidence", "reviewed_without_determination", "closed_as_laboratory_example"}
ITEM_STATES = {"not_reviewed", "reviewed", "additional_evidence_required", "unresolved", "not_resolvable_in_current_scope", "not_applicable"}
QUESTION_STATES = {"reviewed", "additional_evidence_required", "not_applicable", "unresolved"}
FINAL_STATUS = {"reviewed_without_determination", "closed_as_laboratory_example"}
REQUIRED_CHECKS = (
    "overview_read", "facts_checked", "key_sources_opened", "timeline_checked", "time_uncertainty_checked",
    "graph_checked", "gaps_checked", "all_hypotheses_checked", "comparison_matrix_opened", "questions_checked",
    "unresolved_items_recorded", "limitations_checked", "no_automatic_action_confirmed",
)
WORKFLOW_STEPS = ("overview", "facts", "timeline", "graph", "gaps", "hypotheses", "comparisons", "questions", "decision")


class ReviewService:
    def __init__(self, db: Database) -> None:
        self.db = db

    def create(self, card_id: str, source_sha256: str, case_id: str = "legacy_case", source_semantic_sha256: str | None = None) -> dict[str, Any]:
        active = self.active_for_card(card_id)
        if active:
            self._audit(active, "review_resumed", {"case_id": active["case_id"]})
            return self._required(active["review_session_id"])
        stamp = now()
        payload = {
            "schema_version":"manual_review_session_v2", "review_session_id":"review_" + uuid.uuid4().hex,
            "case_id":case_id, "card_id":card_id, "source_card_id":card_id, "source_bundle_sha256":source_sha256,
            "source_semantic_sha256":source_semantic_sha256 or source_sha256, "status":"in_review", "current_step":"overview",
            "completed_step_ids":[], "reviewed_fact_ids":[], "reviewed_relation_ids":[], "reviewed_gap_ids":[],
            "reviewed_hypothesis_ids":[], "reviewed_comparison_ids":[], "reviewed_question_ids":[],
            "unresolved_item_ids":[], "item_states":{}, "checklist":{item:False for item in REQUIRED_CHECKS},
            "notes":[], "decision":None, "created_at":stamp, "updated_at":stamp, "completed_at":None,
            "reviewer_role":"laboratory_admin", "audit_event_ids":[], "version":1,
            "safety":{"no_final_determination":True,"no_automatic_action":True,"source_artifacts_modified":False},
        }
        with self.db.connect() as con:
            con.execute("INSERT INTO reviews VALUES(?,?,?,?,?,?,?)", (payload["review_session_id"], card_id, source_sha256, payload["status"], json.dumps(payload, ensure_ascii=False), stamp, stamp))
            con.execute("INSERT INTO review_versions(review_id,version,occurred_at,action,payload) VALUES(?,?,?,?,?)", (payload["review_session_id"], 1, stamp, "review_created", json.dumps(payload, ensure_ascii=False)))
        self._audit(payload, "review_created", {"case_id":case_id})
        return self._required(payload["review_session_id"])

    def active_for_card(self, card_id: str) -> dict[str, Any] | None:
        with self.db.connect() as con:
            row = con.execute("SELECT payload FROM reviews WHERE card_id=? AND status IN ('not_started','in_review','needs_additional_evidence') ORDER BY updated_at DESC LIMIT 1", (card_id,)).fetchone()
        return json.loads(row[0]) if row else None

    def _ensure_mutable(self, payload: dict[str, Any]) -> None:
        if payload["status"] in FINAL_STATUS:
            raise ValueError("completed_review_immutable")

    def _save(self, payload: dict[str, Any], action: str = "review_saved") -> None:
        payload["updated_at"] = now(); payload["version"] = int(payload.get("version", 1)) + 1
        encoded = json.dumps(payload, ensure_ascii=False)
        with self.db.connect() as con:
            con.execute("UPDATE reviews SET status=?,payload=?,updated_at=? WHERE id=?", (payload["status"], encoded, payload["updated_at"], payload["review_session_id"]))
            con.execute("INSERT INTO review_versions(review_id,version,occurred_at,action,payload) VALUES(?,?,?,?,?)", (payload["review_session_id"], payload["version"], payload["updated_at"], action, encoded))
        self._audit(payload, action)

    def _audit(self, payload: dict[str, Any], action: str, detail: dict[str, Any] | None = None) -> None:
        event = self.db.audit(action, payload["review_session_id"], "success", detail)
        payload["audit_event_ids"].append(event)
        with self.db.connect() as con:
            con.execute("UPDATE reviews SET payload=? WHERE id=?", (json.dumps(payload, ensure_ascii=False), payload["review_session_id"]))

    def get(self, review_id: str) -> dict[str, Any] | None:
        with self.db.connect() as con:
            row = con.execute("SELECT payload FROM reviews WHERE id=?", (review_id,)).fetchone()
        return json.loads(row[0]) if row else None

    def list(self, card_id: str | None = None) -> list[dict[str, Any]]:
        with self.db.connect() as con:
            if card_id:
                rows = con.execute("SELECT payload FROM reviews WHERE card_id=? ORDER BY created_at DESC", (card_id,))
            else:
                rows = con.execute("SELECT payload FROM reviews ORDER BY created_at DESC")
            return [json.loads(row[0]) for row in rows]

    def history(self, review_id: str) -> list[dict[str, Any]]:
        self._required(review_id)
        with self.db.connect() as con:
            return [{"version":row["version"],"occurred_at":row["occurred_at"],"action":row["action"]} for row in con.execute("SELECT version,occurred_at,action FROM review_versions WHERE review_id=? ORDER BY version", (review_id,))]

    def update_progress(self, review_id: str, current_step: str, completed_step_ids: list[str], unresolved_item_ids: list[str]) -> dict[str, Any]:
        if current_step not in WORKFLOW_STEPS or any(step not in WORKFLOW_STEPS for step in completed_step_ids):
            raise ValueError("unknown_workflow_step")
        payload = self._required(review_id); self._ensure_mutable(payload)
        payload["current_step"] = current_step; payload["completed_step_ids"] = sorted(set(completed_step_ids), key=WORKFLOW_STEPS.index)
        payload["unresolved_item_ids"] = sorted(set(unresolved_item_ids)); self._save(payload, "review_progress_saved")
        return self._required(review_id)

    def set_item_state(self, review_id: str, entity_type: str, entity_id: str, state: str) -> dict[str, Any]:
        allowed_types = {"fact":"reviewed_fact_ids","relation":"reviewed_relation_ids","gap":"reviewed_gap_ids","hypothesis":"reviewed_hypothesis_ids","comparison":"reviewed_comparison_ids","question":"reviewed_question_ids"}
        if entity_type not in allowed_types: raise ValueError("unknown_review_entity_type")
        allowed_states = QUESTION_STATES if entity_type == "question" else ITEM_STATES
        if state not in allowed_states or (entity_type == "gap" and state == "resolved"): raise ValueError("unknown_manual_state")
        payload = self._required(review_id); self._ensure_mutable(payload)
        key = f"{entity_type}:{entity_id}"; payload["item_states"][key] = state
        collection = payload[allowed_types[entity_type]]
        if state in {"reviewed", "additional_evidence_required", "unresolved", "not_resolvable_in_current_scope", "not_applicable"} and entity_id not in collection: collection.append(entity_id)
        if state in {"additional_evidence_required", "unresolved"} and entity_id not in payload["unresolved_item_ids"]: payload["unresolved_item_ids"].append(entity_id)
        self._save(payload, f"review_{entity_type}_state_saved"); return self._required(review_id)

    def add_check(self, review_id: str, item_id: str, checked: bool) -> dict[str, Any]:
        payload = self._required(review_id); self._ensure_mutable(payload)
        if item_id not in payload["checklist"]: payload["checklist"][item_id] = False
        payload["checklist"][item_id] = bool(checked); self._save(payload, "review_check_saved"); return self._required(review_id)

    def add_note(self, review_id: str, text: str) -> dict[str, Any]:
        if not text.strip() or len(text) > 4000 or "<" in text or ">" in text: raise ValueError("unsafe_review_note")
        payload = self._required(review_id); self._ensure_mutable(payload)
        payload["notes"].append({"schema_version":"manual_review_note_v2","note_id":"note_" + uuid.uuid4().hex,"revision":1,"text":text.strip(),"created_at":now(),"updated_at":now(),"is_evidence":False,"history":[]})
        self._save(payload, "review_note_added"); return self._required(review_id)

    def decide(self, review_id: str, status: str, limitations: list[str], next_manual_step: str, operator_summary: str = "Рассмотрение выполнено в пределах лабораторных данных.") -> dict[str, Any]:
        if status not in ALLOWED_STATUS or status in {"not_started", "in_review"}: raise ValueError("forbidden_review_status")
        payload = self._required(review_id); self._ensure_mutable(payload)
        payload["status"] = status
        payload["decision"] = {"schema_version":"manual_review_decision_v2","no_final_determination":True,"no_automatic_action":True,
                               "reviewed_sections":payload["completed_step_ids"],"unresolved_items":payload["unresolved_item_ids"],
                               "additional_evidence_required":status == "needs_additional_evidence","operator_summary":operator_summary,
                               "next_manual_step":next_manual_step,"limitations":limitations}
        self._save(payload, "review_decision_recorded"); return self._required(review_id)

    def complete(self, review_id: str, operator_summary: str, next_manual_step: str, limitations: list[str]) -> dict[str, Any]:
        payload = self._required(review_id); self._ensure_mutable(payload)
        missing = [key for key in REQUIRED_CHECKS if not payload["checklist"].get(key)]
        missing_steps = [step for step in WORKFLOW_STEPS[:-1] if step not in payload["completed_step_ids"]]
        if missing or missing_steps: raise ValueError("mandatory_review_steps_incomplete")
        payload["status"] = "reviewed_without_determination"; payload["current_step"] = "decision"; payload["completed_step_ids"] = list(WORKFLOW_STEPS)
        payload["decision"] = {"schema_version":"manual_review_decision_v2","no_final_determination":True,"no_automatic_action":True,
                               "reviewed_sections":list(WORKFLOW_STEPS),"unresolved_items":payload["unresolved_item_ids"],
                               "additional_evidence_required":bool(payload["unresolved_item_ids"]),"operator_summary":operator_summary,
                               "next_manual_step":next_manual_step,"limitations":limitations}
        payload["completed_at"] = now(); self._save(payload, "review_completed"); return self._required(review_id)

    def export(self, review_id: str) -> dict[str, Any]:
        payload = self._required(review_id)
        semantic = {"schema_version":"manual_review_export_v2","case_id":payload["case_id"],"card_id":payload["card_id"],
                    "source_bundle_sha256":payload["source_bundle_sha256"],"source_semantic_sha256":payload["source_semantic_sha256"],
                    "review_session_id":payload["review_session_id"],"completed_steps":payload["completed_step_ids"],
                    "reviewed_entities":{key:payload[key] for key in ("reviewed_fact_ids","reviewed_relation_ids","reviewed_gap_ids","reviewed_hypothesis_ids","reviewed_comparison_ids","reviewed_question_ids")},
                    "unresolved_items":payload["unresolved_item_ids"],"notes":[{"note_id":n["note_id"],"revision":n.get("revision",1),"text":n["text"],"is_evidence":False} for n in payload["notes"]],
                    "decision":payload["decision"],"limitations":payload["decision"]["limitations"] if payload["decision"] else [],
                    "no_final_determination":True,"no_automatic_action":True,"audit_summary":{"event_count":len(payload["audit_event_ids"])},
                    "safety":{"source_artifacts_modified":False,"test_oracle_included":False,"secrets_included":False}}
        digest = semantic_sha(semantic); manifest = {"schema_version":"manual_review_export_manifest_v1","semantic_sha256":digest,"file_count":1}
        return {**semantic,"manifest":manifest,"export_sha256":semantic_sha({**semantic,"manifest":manifest})}

    def progress(self, review_id: str) -> dict[str, Any]:
        payload = self._required(review_id); missing = [key for key in REQUIRED_CHECKS if not payload["checklist"].get(key)]
        return {"schema_version":"operator_workflow_progress_v1","review_session_id":review_id,"current_step":payload["current_step"],
                "completed_step_ids":payload["completed_step_ids"],"missing_required_checks":missing,"unresolved_item_ids":payload["unresolved_item_ids"],
                "unsaved_changes":False,"completion_allowed":not missing and all(x in payload["completed_step_ids"] for x in WORKFLOW_STEPS[:-1])}

    def _required(self, review_id: str) -> dict[str, Any]:
        payload = self.get(review_id)
        if not payload: raise KeyError("review_not_found")
        return copy.deepcopy(payload)
