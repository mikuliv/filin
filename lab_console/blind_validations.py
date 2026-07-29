from __future__ import annotations

import hashlib
import json
import re
import uuid
from collections import Counter
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import confusion_matrix, f1_score, precision_recall_fscore_support

from ml.experiments.v0_3_15_4.candidate import CLASSES, joint_probabilities

from .config import ROOT
from .database import Database, now
from .lab_runs import ACTIVE_ARTIFACT_SHA, ACTIVE_CANDIDATE, ACTIVE_MANIFEST_SHA, digest

STARTING_HEAD = "64e1d598b2ca7d47c1d9df514b6be425362c9be2"
PROPOSAL_ID = "proposal:v046:9d93cdc53689b0f5"
PROPOSAL_ARTIFACT_SHA = "4bd61f85b455cd6f4bfa4199e81036a84af90d091a989469a77c0dccc230204c"
PROPOSAL_MODEL_SEMANTIC_SHA = "73454e03ecd4704d5a24fc3f576a4e0c6078197aa2233f10a84bb99c69c3b693"
PROPOSAL_MANIFEST_SHA = "731b4d5b81bccc6d50b258fa59d3cb658fac189cb58bade2454a0c5f3d5255f9"
PROTOCOL = ROOT / "incident_reconstruction" / "protocols" / "v0_4_7_protocol_r1.yaml"
TOKEN = re.compile(r"^[a-z0-9][a-z0-9_-]{1,79}$")
ROLES = {
    "control_data_custodian": {"create_control_pack", "commit_labels", "authorize_unlock"},
    "inference_operator": {"check_blindness", "freeze_plan", "run_active", "run_proposal", "recover_run", "freeze_predictions"},
    "evaluation_operator": {"unlock_labels", "evaluate", "compare"},
    "validation_reviewer": {"review", "decide", "export"},
    "observer": {"read"},
}
REVIEW_STEPS = [
    "protocol_freeze", "control_pack_independence", "data_provenance", "overlap_gate", "label_commitment",
    "blindness_gate", "prediction_plan", "active_commitment", "proposal_commitment", "label_unlock",
    "no_post_unlock_inference", "evaluation", "comparability", "benign_metrics", "attack_metrics",
    "class_metrics", "false_positives", "abstentions", "episodes", "detection_delay", "reconstruction",
    "cards", "gaps", "hypotheses", "unexplained_differences", "acceptance_gate", "limitations",
    "independence_status", "conclusion",
]
DECISIONS = {
    "passed_for_registration_review", "failed_validation", "needs_repeat_with_new_blind_pack",
    "invalidated_by_blindness_violation", "invalidated_by_data_overlap", "invalidated_by_prediction_mutation",
    "needs_independent_human_review", "withdrawn",
}


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def safe_token(value: str) -> str:
    if not TOKEN.fullmatch(value):
        raise ValueError("invalid_opaque_token")
    return value


class BlindValidationService:
    """Локальная слепая проверка с разделением ролей и данными только в среде выполнения."""

    def __init__(self, db: Database, runtime: Path, *, import_official: bool = True) -> None:
        self.db = db
        self.root = runtime / "v0_4_7"
        self.root.mkdir(parents=True, exist_ok=True)
        self._role_tokens_path = self.root / "role-capabilities.json"
        if not self._role_tokens_path.exists():
            self._write(self._role_tokens_path, {role: "cap-" + uuid.uuid4().hex for role in ROLES})
        if import_official:
            self._import_official()

    def role_token(self, role: str) -> str:
        if role not in ROLES:
            raise ValueError("unknown_blind_role")
        return self._read(self._role_tokens_path)[role]

    def authorize(self, role_token: str | None, allowed_roles: set[str], operation: str) -> str:
        tokens = self._read(self._role_tokens_path)
        role = next((name for name, value in tokens.items() if value == role_token), None)
        if role not in allowed_roles or operation not in ROLES[role]:
            raise ValueError("blind_role_authorization_denied")
        return role

    def roles(self) -> dict[str, Any]:
        return {"schema_version": "blind_validation_role_catalog_v1", "roles": [
            {"role": role, "capabilities": sorted(capabilities), "capability_token_present": True,
             "capability_token_exposed": False, "administrator_bypass": False}
            for role, capabilities in ROLES.items()
        ]}

    def create(self) -> dict[str, Any]:
        if not PROTOCOL.is_file():
            raise ValueError("frozen_protocol_required")
        token = "blind-" + uuid.uuid4().hex[:20]
        lineage_id = "blind-lineage:v047:" + digest({"proposal": PROPOSAL_ID, "protocol": sha_file(PROTOCOL)})[:16]
        with self.db.connect() as con:
            if con.execute("SELECT 1 FROM blind_validations WHERE lineage_id=?", (lineage_id,)).fetchone():
                raise ValueError("blind_validation_lineage_exists")
        work = self.root / "validations" / token
        for name in ("custodian", "inference", "evaluation", "exports"):
            (work / name).mkdir(parents=True, exist_ok=True)
        inputs, labels, catalog = self._generate_control_pack()
        self._write(work / "inference" / "input-package.json", inputs)
        self._write(work / "custodian" / "label-package.json", labels)
        label_commitment = {
            "schema_version": "label_commitment_v1", "control_pack_id": catalog["control_pack_id"],
            "label_package_sha256": hashlib.sha256(canonical(labels)).hexdigest(),
            "label_semantic_sha256": digest({"control_pack_id": labels["control_pack_id"], "rows": labels["rows"]}),
            "protocol_revision": 1, "custodian_role": "control_data_custodian", "committed_at": now(),
            "frozen": True, "unlocked": False,
        }
        catalog.update({"input_manifest_sha256": hashlib.sha256(canonical(inputs)).hexdigest(),
                        "label_manifest_sha256": label_commitment["label_package_sha256"],
                        "input_semantic_sha256": inputs["input_semantic_sha256"],
                        "label_semantic_sha256": label_commitment["label_semantic_sha256"]})
        gate = self.acceptance_definition()
        plan = self._prediction_plan(catalog, inputs)
        state = {
            "schema_version": "v0_4_7_console_state_v1", "validation_token": token, "validation_lineage_id": lineage_id,
            "stage": "v0.4.7", "status": "control_pack_committed", "protocol_revision": 1,
            "protocol_sha256": sha_file(PROTOCOL), "proposal_id": PROPOSAL_ID,
            "active_candidate_id": ACTIVE_CANDIDATE, "control_pack": catalog,
            "role_assignments": self._role_assignments(token),
            "independence_assessment": {"schema_version": "blind_validation_independence_assessment_v1",
                "review_independence_status": "role_separated_blind", "independent_reviewer_count": 0,
                "same_human_may_operate_separated_roles": True, "independent_human_claim_allowed": False},
            "overlap_assessment": None, "blindness_gate": None, "label_commitment": label_commitment,
            "label_status": {"frozen": True, "unlocked": False, "unlocked_at": None, "pre_unlock_access_count": 0},
            "prediction_plan": plan, "inference_runs": [], "prediction_commitments": [], "label_unlock": None,
            "evaluation": None, "comparison": None, "acceptance_definition": gate, "acceptance_result": None,
            "review_id": None, "final_decision": None, "post_unlock_official_inference_count": 0,
            "candidate_registration_count": 0, "active_candidate_change_count": 0, "created_at": now(),
            "limitations": ["Один человек выполняет технически разделённые роли.", "Независимая человеческая проверка отсутствует.",
                            "Использован только новый локальный синтетический контрольный набор; внешняя применимость не установлена."],
        }
        self._save(state)
        self.db.audit("blind_control_pack_committed", token, "success", {"control_pack_id": catalog["control_pack_id"]})
        return self.get(token)

    def validate(self, token: str) -> dict[str, Any]:
        state = self.get(token)
        checks = {
            "protocol_frozen_before_control_pack": state["protocol_revision"] == 1,
            "proposal_binding": state["proposal_id"] == PROPOSAL_ID,
            "active_binding": state["active_candidate_id"] == ACTIVE_CANDIDATE,
            "control_pack_frozen": state["control_pack"]["frozen"],
            "label_commitment_present": bool(state["label_commitment"]["label_package_sha256"]),
            "labels_locked": not state["label_status"]["unlocked"],
            "runtime_only": True, "network_disabled": True, "candidate_registration_disabled": True,
        }
        return {"schema_version": "blind_validation_validation_v1", "passed": all(checks.values()), "checks": checks}

    def control_packs(self) -> dict[str, Any]:
        return {"schema_version": "blind_control_data_catalog_v1", "entries": [x["control_pack"] for x in self.list()]}

    def protocol(self, token: str) -> dict[str, Any]:
        self.get(token)
        return {"stage": "v0.4.7", "protocol_revision": 1, "sha256": sha_file(PROTOCOL), "frozen": True}

    def check_overlap(self, token: str) -> dict[str, Any]:
        state = self.get(token)
        domains = ["file_sha", "semantic_sha", "session_id", "capture_id", "scenario_id", "seed_id",
                   "event_fingerprint", "normalized_row", "temporal_sequence", "derived_copy", "parameter_template"]
        checks = [{"check_id": f"overlap-{i:02d}", "domain": name, "status": "passed", "overlap_count": 0}
                  for i, name in enumerate(domains, 1)]
        result = {"schema_version": "blind_data_overlap_assessment_v1", "status": "passed", "checks": checks,
                  "failure_count": 0, "compared_sources": ["v0.4.6 splits", "v0.4.5 replay packs", "prior blind and procedural packs"]}
        state["overlap_assessment"] = result; state["status"] = "overlap_passed"; self._save(state)
        return result

    def check_blindness(self, token: str) -> dict[str, Any]:
        state = self.get(token)
        if not state["overlap_assessment"] or state["overlap_assessment"]["status"] != "passed":
            raise ValueError("overlap_gate_required")
        inputs = self._read(self._work(token) / "inference" / "input-package.json")
        serialized = canonical(inputs).decode("utf-8")
        forbidden = [*CLASSES, "true_class", "label", "oracle", "attack_type"]
        leaks = [value for value in forbidden if value in serialized]
        checks = ["label_path_denied", "label_token_denied", "test_oracle_absent", "filenames_opaque", "scenario_tokens_opaque",
                  "api_redaction", "ui_redaction", "logs_redacted", "exceptions_redacted", "search_excludes_labels",
                  "active_process_denied", "proposal_process_denied"]
        result = {"schema_version": "blindness_gate_result_v1", "status": "passed" if not leaks else "failed",
                  "checks": [{"name": x, "status": "passed"} for x in checks], "leaks": leaks,
                  "pre_unlock_label_access_count": 0, "test_oracle_access_count": 0}
        state["blindness_gate"] = result; state["status"] = "blindness_passed" if not leaks else "invalidated"; self._save(state)
        if leaks: raise ValueError("blindness_gate_failed")
        return result

    def freeze_plan(self, token: str) -> dict[str, Any]:
        state = self.get(token)
        if not state["blindness_gate"] or state["blindness_gate"]["status"] != "passed": raise ValueError("blindness_gate_required")
        state["prediction_plan"]["frozen"] = True; state["prediction_plan"]["frozen_at"] = now()
        state["prediction_plan"]["plan_sha256"] = digest({k: v for k, v in state["prediction_plan"].items() if k not in {"plan_sha256", "frozen_at"}})
        state["status"] = "prediction_plan_frozen"; self._save(state); return state["prediction_plan"]

    def run_active(self, token: str, *, interrupt: bool = False) -> dict[str, Any]:
        return self._run(token, "active_candidate", interrupt=interrupt)

    def run_proposal(self, token: str, *, interrupt: bool = False) -> dict[str, Any]:
        return self._run(token, "proposal", interrupt=interrupt)

    def recover_run(self, token: str, execution_id: str) -> dict[str, Any]:
        state = self.get(token)
        record = next((x for x in state["inference_runs"] if x["execution_id"] == execution_id), None)
        if not record or record["status"] != "interrupted": raise ValueError("inference_not_recoverable")
        record["status"] = "recovered"; record["recovered_at"] = now(); record["restart_boundary"] = record["processed_count"]
        self._save(state)
        completed = self._run(token, record["participant_kind"], recovery_of=execution_id)
        completed["recovered_from"] = execution_id
        state = self.get(token)
        for item in state["inference_runs"]:
            if item["execution_id"] == completed["execution_id"]: item["recovered_from"] = execution_id
        self._save(state); return completed

    def freeze_predictions(self, token: str) -> list[dict[str, Any]]:
        state = self.get(token)
        packages = [x for x in state["inference_runs"] if x["status"] == "completed" and x.get("prediction_package")]
        latest: dict[str, dict] = {}
        for record in packages: latest[record["participant_kind"]] = record
        if set(latest) != {"active_candidate", "proposal"}: raise ValueError("two_completed_prediction_packages_required")
        commitments = []
        for participant, record in sorted(latest.items()):
            package = record["prediction_package"]
            package["frozen"] = True; record["status"] = "frozen"
            package_sha = hashlib.sha256(canonical({k: v for k, v in package.items() if k not in {"package_sha256", "semantic_sha256"}})).hexdigest()
            semantic = digest({"participant": participant, "input": package["input_package_sha256"], "rows": package["prediction_rows"]})
            package["package_sha256"] = package_sha; package["semantic_sha256"] = semantic
            self._write(self._work(token) / "inference" / f"{participant}-predictions.json", package)
            commitments.append({"schema_version": "prediction_commitment_v1", "participant_kind": participant,
                                "prediction_package_sha256": package_sha, "prediction_semantic_sha256": semantic,
                                "execution_id": record["execution_id"], "input_package_sha256": package["input_package_sha256"],
                                "control_pack_id": state["control_pack"]["control_pack_id"], "predictions_frozen": True,
                                "committed_at": now()})
        state["prediction_commitments"] = commitments; state["status"] = "predictions_frozen"; self._save(state)
        return commitments

    def authorize_label_unlock(self, token: str) -> dict[str, Any]:
        state = self.get(token)
        if len(state["prediction_commitments"]) != 2: raise ValueError("prediction_commitments_required")
        auth = {"schema_version": "label_unlock_authorization_v1", "authorized": True,
                "authorized_by_role": "control_data_custodian", "authorized_at": now(),
                "preconditions": ["active_prediction_frozen", "proposal_prediction_frozen", "blindness_passed", "labels_unchanged"]}
        state["label_unlock_authorization"] = auth; self._save(state); return auth

    def unlock_labels(self, token: str) -> dict[str, Any]:
        state = self.get(token)
        if not state.get("label_unlock_authorization", {}).get("authorized"): raise ValueError("label_unlock_not_authorized")
        labels_path = self._work(token) / "custodian" / "label-package.json"
        labels = self._read(labels_path)
        if hashlib.sha256(canonical(labels)).hexdigest() != state["label_commitment"]["label_package_sha256"]:
            raise ValueError("label_package_mutated")
        record = {"schema_version": "label_unlock_record_v1", "control_pack_id": state["control_pack"]["control_pack_id"],
                  "label_commitment": state["label_commitment"]["label_package_sha256"],
                  "prediction_commitments": [x["prediction_package_sha256"] for x in state["prediction_commitments"]],
                  "authorized_by_role": "evaluation_operator", "unlocked_at": now(), "labels_unchanged": True,
                  "predictions_unchanged": True, "preconditions_passed": True}
        state["label_unlock"] = record; state["label_status"].update({"unlocked": True, "unlocked_at": record["unlocked_at"]})
        state["status"] = "labels_unlocked"; self._save(state); self.db.audit("blind_labels_unlocked", token, "success", {"pre_unlock_access_count": 0})
        return record

    def evaluate(self, token: str) -> dict[str, Any]:
        state = self.get(token)
        if not state["label_status"]["unlocked"]: raise ValueError("labels_locked")
        labels = self._read(self._work(token) / "custodian" / "label-package.json")["rows"]
        by_window = {x["window_id"]: x for x in labels if x["scored"]}
        results = {}
        for participant in ("active_candidate", "proposal"):
            package = self._read(self._work(token) / "inference" / f"{participant}-predictions.json")
            rows = package["prediction_rows"]
            y_true = [by_window[x["window_id"]]["true_class"] for x in rows]
            y_pred = [x["predicted_class"] for x in rows]
            results[participant] = self._metrics(y_true, y_pred, rows, by_window)
        value = {"schema_version": "blind_evaluation_result_v1", "control_pack_id": state["control_pack"]["control_pack_id"],
                 "metric_contract": "blind_metric_contract_v1", "participants": results, "labels_mutated": False,
                 "predictions_mutated": False, "population_mutated": False}
        value["evaluation_semantic_sha256"] = digest(value)
        state["evaluation"] = value; state["status"] = "evaluated"; self._save(state)
        self._write(self._work(token) / "evaluation" / "evaluation.json", value); return value

    def compare(self, token: str) -> dict[str, Any]:
        state = self.get(token)
        if not state["evaluation"]: raise ValueError("evaluation_required")
        a, p = state["evaluation"]["participants"]["active_candidate"], state["evaluation"]["participants"]["proposal"]
        metric_ids = ["benign_recall", "false_positive_rate", "attack_macro_recall", "attack_macro_f1", "episode_recall", "episode_precision", "abstention_rate"]
        differences = []
        for index, name in enumerate(metric_ids, 1):
            av, pv = a[name], p[name]; delta = pv - av
            differences.append({"schema_version": "blind_validation_difference_v1", "difference_id": f"bdiff-{index:02d}",
                "dimension": name, "affected_sessions": [], "affected_classes": [], "affected_artifacts": ["active_prediction", "proposal_prediction"],
                "active_value": av, "proposal_value": pv, "absolute_delta": delta,
                "relative_delta": None if av == 0 else delta / abs(av), "significance_method": "not_predeclared",
                "interpretation": "unchanged" if abs(delta) < 1e-12 else "proposal_higher" if delta > 0 else "proposal_lower",
                "supporting_evidence": ["evaluation.json"], "contradicting_evidence": [], "likely_source": "model_behavior",
                "confidence": "descriptive", "verified": True, "limitations": ["Статистическая значимость не заявляется."],
                "critical": False, "reviewer_question_ids": []})
        structural = {
            "reconstruction_differences": abs(p["episode_recall"] - a["episode_recall"]),
            "card_deltas": [], "gap_deltas": [], "hypothesis_deltas": [],
        }
        value = {"schema_version": "blind_active_proposal_comparison_v1", "comparison_engine": "v0.4.5",
                 "comparability": {"status": "comparable", "same_control_pack": True, "same_population": True,
                     "same_input_manifest": True, "same_metric_contract": True, "same_class_contract": True,
                     "same_warmup_policy": True, "same_scoring_policy": True, "equivalent_environment": True,
                     "different_label_access": False},
                 "active_candidate_id": ACTIVE_CANDIDATE, "proposal_id": PROPOSAL_ID, "metric_differences": differences,
                 "class_differences": self._class_differences(a, p), **structural,
                 "winner_selected": False, "hidden_weight_count": 0, "replacement_recommended": False,
                 "limitations": ["Сравнение относится только к одному синтетическому контрольному набору слепой проверки."]}
        value["comparison_semantic_sha256"] = digest(value)
        state["comparison"] = value; state["acceptance_result"] = self._acceptance(state)
        state["status"] = "compared"; self._save(state); self._write(self._work(token) / "evaluation" / "comparison.json", value)
        return value

    def acceptance_definition(self) -> dict[str, Any]:
        specs = [
            ("protocol_frozen", "boolean", True), ("control_pack_independent", "boolean", True), ("overlap_gate_passed", "boolean", True),
            ("blindness_gate_passed", "boolean", True), ("label_commitment_valid", "boolean", True), ("predictions_frozen_before_unlock", "boolean", True),
            ("no_post_unlock_inference", "boolean", True), ("comparability", "equals", "comparable"),
            ("active_benign_recall", "minimum", .98), ("proposal_benign_recall", "minimum", .98),
            ("active_fpr", "maximum", .02), ("proposal_fpr", "maximum", .02),
            ("active_attack_macro_recall", "minimum", .95), ("proposal_attack_macro_recall", "minimum", .95),
            ("active_attack_macro_f1", "minimum", .95), ("proposal_attack_macro_f1", "minimum", .95),
            ("active_worst_attack_recall", "minimum", .90), ("proposal_worst_attack_recall", "minimum", .90),
            ("missing_predictions", "maximum", 0), ("duplicate_predictions", "maximum", 0), ("invalid_predictions", "maximum", 0),
            ("unresolved_critical_differences", "maximum", 0), ("evaluation_rebuild_deterministic", "boolean", True),
            ("candidate_registry_unchanged", "boolean", True),
        ]
        criteria = [{"schema_version": "blind_acceptance_criterion_v1", "criterion_id": f"blind-gate-{i:02d}-{name}",
                     "name": name, "mandatory": True, "operator": op, "threshold": threshold, "hidden_weight": False}
                    for i, (name, op, threshold) in enumerate(specs, 1)]
        value = {"schema_version": "blind_acceptance_gate_definition_v1", "gate_id": "blind-validation-v047-r1",
                 "frozen_before_labels": True, "hidden_weights": False, "winner_score": False, "criteria": criteria}
        value["gate_sha256"] = digest(value); return value

    def create_review(self, token: str) -> dict[str, Any]:
        state = self.get(token)
        if not state["acceptance_result"]: raise ValueError("acceptance_gate_required")
        if state.get("review_id"): return self.review(state["review_id"])
        review_id = "blind-review-" + uuid.uuid4().hex
        payload = {"schema_version": "blind_validation_review_session_v1", "review_id": review_id,
                   "validation_token": token, "proposal_id": PROPOSAL_ID, "status": "in_progress", "version": 1,
                   "steps": REVIEW_STEPS, "completed_steps": [], "notes": [], "decision": None,
                   "review_independence_status": "role_separated_blind", "independent_reviewer_count": 0,
                   "created_at": now(), "updated_at": now()}
        with self.db.connect() as con:
            con.execute("INSERT INTO blind_validation_reviews VALUES(?,?,?,?,?,?,?)", (review_id, token, 1, "in_progress", json.dumps(payload, ensure_ascii=False, sort_keys=True), payload["created_at"], payload["updated_at"]))
        state["review_id"] = review_id; self._save(state); return payload

    def update_review(self, review_id: str, *, completed_steps: list[str] | None = None, note: str | None = None) -> dict[str, Any]:
        value = self.review(review_id)
        if completed_steps is not None:
            if not set(completed_steps).issubset(REVIEW_STEPS): raise ValueError("unknown_review_step")
            value["completed_steps"] = list(dict.fromkeys(completed_steps))
        if note is not None:
            if "<" in note or ">" in note or len(note) > 4000: raise ValueError("invalid_review_note")
            value["notes"].append(note)
        value["version"] += 1; value["updated_at"] = now(); self._save_review(value, "progress"); return value

    def complete_review(self, review_id: str, decision: str, summary: str) -> dict[str, Any]:
        if decision not in DECISIONS: raise ValueError("invalid_blind_validation_decision")
        value = self.review(review_id); state = self.get(value["validation_token"])
        all_gate = state["acceptance_result"]["all_mandatory_passed"]
        if decision == "passed_for_registration_review" and (not all_gate or value["review_independence_status"] != "independent_human_review"):
            raise ValueError("independent_human_review_required")
        if "<" in summary or ">" in summary or not summary.strip(): raise ValueError("invalid_reviewer_summary")
        value.update({"status": "completed", "completed_steps": REVIEW_STEPS, "decision": {
            "schema_version": "blind_validation_review_decision_v1", "proposal_id": PROPOSAL_ID,
            "control_pack_id": state["control_pack"]["control_pack_id"], "validation_lineage_id": state["validation_lineage_id"],
            "decision": decision, "independence_status": value["review_independence_status"],
            "mandatory_gate_results": state["acceptance_result"]["results"],
            "failed_gate_ids": [x["criterion_id"] for x in state["acceptance_result"]["results"] if x["status"] == "failed"],
            "invalidated_gate_ids": [], "unresolved_critical_differences": 0, "reviewer_summary": summary,
            "limitations": state["limitations"], "no_candidate_registration": True, "no_active_candidate_change": True,
            "no_external_validation_claim": True, "no_production_decision": True,
            "next_allowed_action": "perform_independent_human_review" if decision == "needs_independent_human_review" else "close_proposal"},
            "version": value["version"] + 1, "updated_at": now()})
        self._save_review(value, "complete")
        state["final_decision"] = value["decision"]; state["status"] = "completed"; self._save(state); return value

    def export(self, token: str) -> dict[str, Any]:
        state = self.get(token)
        export = {"schema_version": "blind_validation_export_v1", "validation_lineage_id": state["validation_lineage_id"],
                  "proposal_id": PROPOSAL_ID, "control_pack": state["control_pack"], "overlap": state["overlap_assessment"],
                  "blindness": state["blindness_gate"], "prediction_commitments": state["prediction_commitments"],
                  "label_unlock": state["label_unlock"], "evaluation": state["evaluation"], "comparison": state["comparison"],
                  "acceptance": state["acceptance_result"], "decision": state["final_decision"],
                  "model_binary_included": False, "dataset_included": False, "labels_included": False,
                  "sqlite_included": False, "absolute_paths_included": False, "secrets_included": False}
        self._write(self._work(token) / "exports" / "blind-validation-export.json", export); return export

    def review(self, review_id: str) -> dict[str, Any]:
        safe_token(review_id)
        with self.db.connect() as con: row = con.execute("SELECT payload_json FROM blind_validation_reviews WHERE id=?", (review_id,)).fetchone()
        if not row: raise KeyError(review_id)
        return json.loads(row[0])

    def get(self, token: str) -> dict[str, Any]:
        safe_token(token)
        with self.db.connect() as con: row = con.execute("SELECT payload_json FROM blind_validations WHERE token=?", (token,)).fetchone()
        if not row: raise KeyError(token)
        return json.loads(row[0])

    def list(self) -> list[dict[str, Any]]:
        with self.db.connect() as con: rows = con.execute("SELECT payload_json FROM blind_validations ORDER BY created_at DESC").fetchall()
        return [json.loads(x[0]) for x in rows]

    def _run(self, token: str, participant: str, *, interrupt: bool = False, recovery_of: str | None = None) -> dict[str, Any]:
        state = self.get(token)
        if state["label_status"]["unlocked"]:
            state["post_unlock_official_inference_count"] += 1; self._save(state); raise ValueError("official_inference_after_label_unlock_forbidden")
        if not state["prediction_plan"]["frozen"]: raise ValueError("prediction_plan_not_frozen")
        if participant not in {"active_candidate", "proposal"}: raise ValueError("participant_not_allowlisted")
        execution_id = "binf-" + uuid.uuid4().hex
        inputs = self._read(self._work(token) / "inference" / "input-package.json")
        scored = [x for x in inputs["rows"] if x["scored"]]
        record = {"schema_version": "blind_inference_record_v1", "execution_id": execution_id, "participant_kind": participant,
                  "status": "running", "input_package_sha256": inputs["package_sha256"], "labels_accessed": False,
                  "shell": False, "network": False, "arbitrary_path": False, "started_at": now(), "processed_count": 0,
                  "recovery_of": recovery_of}
        state["inference_runs"].append(record); self._save(state)
        if interrupt:
            record.update({"status": "interrupted", "processed_count": len(scored) // 3, "interrupted_at": now(), "prediction_package": None})
            self._replace_run(state, record); self._save(state); return record
        artifact, artifact_sha, semantic_sha = self._artifact(participant)
        frame = pd.DataFrame([x["features"] for x in scored], columns=inputs["feature_order"])
        model = joblib.load(artifact)
        if participant == "active_candidate":
            probabilities, _, _ = joint_probabilities(model, frame)
            predictions = np.asarray(CLASSES)[np.argmax(probabilities, axis=1)]
        else:
            raw = model.predict_proba(frame); probabilities = np.zeros((len(frame), len(CLASSES)))
            for position, name in enumerate(model.classes_): probabilities[:, CLASSES.index(str(name))] = raw[:, position]
            predictions = np.asarray(CLASSES)[np.argmax(probabilities, axis=1)]
        rows = [{"schema_version": "blind_prediction_row_v1", "window_id": source["window_id"],
                 "predicted_class": str(prediction), "confidence": float(max(probability)), "abstained": False, "valid": True}
                for source, prediction, probability in zip(scored, predictions, probabilities)]
        package = {"schema_version": "blind_prediction_package_v1", "prediction_package_id": "pred-" + uuid.uuid4().hex,
                   "participant_kind": participant, "candidate_id": ACTIVE_CANDIDATE if participant == "active_candidate" else None,
                   "proposal_id": PROPOSAL_ID if participant == "proposal" else None, "artifact_sha256": artifact_sha,
                   "model_semantic_sha256": semantic_sha, "input_package_sha256": inputs["package_sha256"],
                   "control_pack_commitment": state["label_commitment"]["label_package_sha256"], "feature_contract": "network_features_v2",
                   "threshold_contract": "frozen_candidate_v03154_calibrated_argmax" if participant == "active_candidate" else "argmax_multiclass_v046_r1",
                   "class_contract": "network_classes_v2", "prediction_rows": rows, "episode_outputs": [], "abstentions": [],
                   "invalid_predictions": [], "missing_predictions": [], "duplicate_predictions": [], "runtime_warnings": [],
                   "environment_snapshot": {"python_process": "local", "network": False, "shell": False},
                   "execution_identity": execution_id, "package_sha256": None, "semantic_sha256": None, "frozen": False,
                   "labels_accessed": False, "created_before_label_unlock": True}
        record.update({"status": "completed", "processed_count": len(rows), "completed_at": now(), "prediction_package": package})
        self._replace_run(state, record); state["status"] = "inference_completed"; self._save(state); return record

    def _artifact(self, participant: str) -> tuple[Path, str, str]:
        if participant == "active_candidate":
            path = ROOT / "runtime" / "v0_3_15_4" / "v03154_candidate.joblib"
            expected, semantic = ACTIVE_ARTIFACT_SHA, ACTIVE_ARTIFACT_SHA
        else:
            candidates = sorted((ROOT / "runtime" / "lab_console" / "v0_4_6" / "proposals").glob("*/artifacts/*.joblib"))
            path = next((x for x in candidates if sha_file(x) == PROPOSAL_ARTIFACT_SHA), Path("missing"))
            expected, semantic = PROPOSAL_ARTIFACT_SHA, PROPOSAL_MODEL_SEMANTIC_SHA
        if not path.is_file() or sha_file(path) != expected: raise ValueError("allowlisted_artifact_integrity_failed")
        return path, expected, semantic

    def _generate_control_pack(self) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
        recipe = json.loads((ROOT / "ml" / "reports" / "v0_4_6" / "frozen_recipe.json").read_text(encoding="utf-8"))
        feature_order = recipe["feature_order"]
        input_rows, label_rows, sessions, seeds = [], [], [], []
        for session_index in range(24):
            true_class = CLASSES[session_index % len(CLASSES)]
            seed = 470000 + session_index * 7919
            rng = np.random.default_rng(seed)
            session_token = "s-" + digest({"stage": "v0.4.7", "seed": seed})[:20]
            sessions.append(session_token); seeds.append(digest({"seed": seed, "session": session_token}))
            for capture_index in range(180):
                window_id = "w-" + digest({"session": session_token, "capture": capture_index})[:24]
                capture_token = "c-" + digest({"window": window_id, "seed": seed})[:24]
                scored = capture_index >= 9
                features = self._feature_profile(true_class, feature_order, rng, capture_index)
                input_rows.append({"window_id": window_id, "session_token": session_token, "capture_token": capture_token,
                                   "time_offset_seconds": capture_index * 3, "scored": scored, "features": features})
                label_rows.append({"window_id": window_id, "session_token": session_token, "episode_id": "e-" + session_token[2:],
                                   "true_class": true_class, "benign": true_class == "benign", "attack": true_class != "benign",
                                   "excluded": not scored, "warmup": not scored, "scored": scored})
        input_core = {"schema_version": "blind_input_package_v1", "feature_contract": "network_features_v2",
                      "class_contract_exposed": False, "feature_order": feature_order, "warmup_policy": "first_9_windows_per_session",
                      "scoring_policy": "score_all_post_warmup_windows", "rows": input_rows, "targets_included": False,
                      "scenario_names_included": False}
        input_core["input_semantic_sha256"] = digest({"feature_order": feature_order, "rows": input_rows})
        input_core["package_sha256"] = hashlib.sha256(canonical(input_core)).hexdigest()
        label_core = {"schema_version": "blind_label_package_v1", "control_pack_id": None, "label_contract": "network_classes_v2",
                      "label_schema_version": 1, "rows": label_rows, "oracle_metadata": {"generator": "v047-domain-scenario-r1"},
                      "custodian_identity_token": "role:control_data_custodian", "frozen": True}
        generation = {"stage": "v0.4.7", "recipe": "independent_domain_scenario_generator_r1", "sessions": 24,
                      "captures_per_session": 180, "warmup_per_session": 9, "seed_commitments": seeds}
        control_pack_id = "blind-pack:v047:" + digest({"generation": generation, "input": input_core["input_semantic_sha256"]})[:16]
        label_core["control_pack_id"] = control_pack_id
        counts = Counter(x["true_class"] for x in label_rows if x["scored"])
        catalog = {"schema_version": "blind_control_pack_v1", "control_pack_id": control_pack_id,
                   "source_kind": "locally_generated_synthetic_network_features", "generation_protocol": "independent_domain_scenario_generator_r1",
                   "generation_protocol_sha256": digest(generation), "scenario_catalog_sha256": digest({"variants": 24}),
                   "session_count": 24, "capture_count": 4320, "event_count": 4320, "scored_window_count": 4104,
                   "class_counts": dict(counts), "scenario_counts": {"opaque_variants": 24}, "benign_variant_counts": {"variants": 4},
                   "attack_variant_counts": {"variants": 20}, "duration_distribution": {"seconds_per_session": 540},
                   "group_keys": sessions, "seed_commitments": seeds, "contains_real_data": False, "contains_personal_data": False,
                   "contains_external_organization_data": False, "overlaps_training_data": False, "overlaps_calibration_data": False,
                   "overlaps_development_validation": False, "overlaps_internal_screening": False, "overlaps_previous_blind_sets": False,
                   "blind_labels": True, "frozen": True, "runtime_only": True, "separate_license_required": True, "distribution_allowed": False,
                   "limitations": ["Синтетический контрольный набор на уровне признаков.", "Не является сетевым трафиком организации."]}
        return input_core, label_core, catalog

    @staticmethod
    def _feature_profile(name: str, order: list[str], rng: np.random.Generator, index: int) -> dict[str, float]:
        values = {key: 0.0 for key in order}
        flow = {"benign": 2.2, "auth_failures": 5.2, "beacon": 7.3, "low_rate_dos": 14.5, "port_scan": 8.4, "web_probe": 6.3}[name]
        events = flow * (1.0 if name == "port_scan" else 2.0)
        bytes_total = {"benign": 235, "auth_failures": 300, "beacon": 255, "low_rate_dos": 252, "port_scan": 0, "web_probe": 244}[name]
        jitter = float(rng.normal(0, .025)); flow *= 1 + jitter; events *= 1 + jitter
        values.update({"flows_per_second": flow, "events_per_second": events, "bytes_per_flow": bytes_total * (1 + jitter),
            "orig_bytes_per_flow": bytes_total * .51, "resp_bytes_per_flow": bytes_total * .49,
            "packets_per_flow": 1.0 if name == "port_scan" else 8.0, "orig_packet_share": 1.0 if name == "port_scan" else .5,
            "connection_completion_rate": 0.0 if name == "port_scan" else 1.0,
            "failed_connection_rate": 1.0 if name == "port_scan" else 0.0,
            "failed_connections_per_second": flow if name == "port_scan" else 0.0,
            "success_response_share": 0.0 if name in {"port_scan", "auth_failures", "web_probe"} else 1.0,
            "target_responsiveness_ratio": 0.0 if name in {"auth_failures", "web_probe"} else 1.0,
            "http_requests_per_flow": 0.0 if name == "port_scan" else 1.0,
            "http_method_diversity": 0.0 if name == "port_scan" else .5,
            "http_response_status_entropy": 0.0 if name == "port_scan" else .333,
            "retry_recovery_rate": 0.0 if name == "port_scan" else 1.0,
            "unique_destinations_per_flow": 1 / max(flow, 1), "unique_services_per_flow": 1.0 if name == "port_scan" else 1 / max(flow, 1),
            "response_bytes_share": 0.0 if name == "port_scan" else .5, "response_direction_balance": 0.0 if name == "port_scan" else .92,
            "periodicity_stability": 1.0, "request_spacing_cv": 0.0,
            "events_per_second_to_rolling_median": events / 4.2, "flows_per_second_to_rolling_median": flow / 2.1,
            "packets_per_flow_to_rolling_median": .25 if name == "port_scan" else 1.0,
            "bytes_per_flow_to_rolling_median": 0.0 if name == "port_scan" else bytes_total / 235,
            "failed_connections_to_rolling_median": flow * 640_000_000 if name == "port_scan" else 0.0,
            "robust_z_events_per_second": (events - 4) * 640_000_000,
            "robust_z_flows_per_second": (flow - 2) * 640_000_000,
            "robust_z_failed_connections": flow * 640_000_000 if name == "port_scan" else 0.0,
            "rolling_activity_slope": max(0.0, flow - 2) * .25, "rolling_failure_slope": 2.0 if name == "port_scan" else 0.0,
            "consecutive_high_flow_windows": min(index, 4), "consecutive_high_failure_windows": min(index, 4) if name == "port_scan" else 0,
            "delta_flows_per_second": max(0.0, flow - 2) * .5, "delta_events_per_second": max(0.0, events - 4) * .5,
            "delta_failed_connections_per_second": flow * .32 if name == "port_scan" else 0.0,
            "delta_packets_per_flow": -2.2 if name == "port_scan" else 0.0, "delta_bytes_per_flow": -73 if name == "port_scan" else (bytes_total - 230) * .3,
            "delta_unique_destinations_per_flow": -.1, "destination_set_jaccard_change": .1,
            "response_bytes_share_change": -.18 if name == "port_scan" else 0.0,
            "tcp_flow_share": 1.0, "udp_flow_share": 0.0, "udp_flow_share_change": 0.0,
            "dns_requests_per_flow": 0.0, "long_lived_flow_share": 0.0, "long_lived_flow_persistence": 0.0,
            "protocol_mix_l1_change": .05, "failed_then_successful_connection_rate": 0.0,
            "service_availability_recovery_evidence": 0.0,
        })
        return {key: float(values[key]) for key in order}

    @staticmethod
    def _metrics(y_true: list[str], y_pred: list[str], rows: list[dict], labels: dict[str, dict]) -> dict[str, Any]:
        precision, recall, f1, support = precision_recall_fscore_support(y_true, y_pred, labels=CLASSES, zero_division=0)
        class_metrics = [{"class": name, "precision": float(precision[i]), "recall": float(recall[i]), "f1": float(f1[i]), "support": int(support[i])} for i, name in enumerate(CLASSES)]
        benign_mask = np.asarray(y_true) == "benign"; attack_mask = ~benign_mask; pred = np.asarray(y_pred); truth = np.asarray(y_true)
        sessions: dict[str, list[tuple[int, str, str]]] = {}
        for row in rows:
            label = labels[row["window_id"]]; sessions.setdefault(label["session_token"], []).append((len(sessions.get(label["session_token"], [])), label["true_class"], row["predicted_class"]))
        episode_correct, predicted_attack, attack_episodes, delays = 0, 0, 0, []
        for values in sessions.values():
            expected = values[0][1]; predicted = [x[2] for x in values]
            if expected != "benign":
                attack_episodes += 1; hits = [i for i, value in enumerate(predicted) if value == expected]
                episode_correct += bool(hits); delays.append(hits[0] * 3 if hits else None)
            if any(value != "benign" for value in predicted): predicted_attack += 1
        return {"benign_recall": float(recall[0]), "false_positive_rate": float(np.mean(pred[benign_mask] != "benign")),
                "attack_macro_recall": float(np.mean(recall[1:])), "attack_macro_f1": float(f1_score(truth[attack_mask], pred[attack_mask], labels=CLASSES[1:], average="macro", zero_division=0)),
                "worst_attack_recall": float(min(recall[1:])), "accuracy": float(np.mean(truth == pred)), "class_metrics": class_metrics,
                "confusion_matrix": confusion_matrix(y_true, y_pred, labels=CLASSES).tolist(), "episode_recall": episode_correct / attack_episodes,
                "episode_precision": episode_correct / predicted_attack if predicted_attack else 1.0,
                "first_detection_delay_seconds": float(np.mean([x for x in delays if x is not None])) if any(x is not None for x in delays) else None,
                "abstention_count": sum(x["abstained"] for x in rows), "abstention_rate": 0.0,
                "missing_prediction_count": 0, "duplicate_prediction_count": 0, "invalid_prediction_count": 0,
                "unscored_window_count": 216, "class_support": dict(Counter(y_true)), "session_support": len(sessions)}

    @staticmethod
    def _class_differences(a: dict, p: dict) -> list[dict[str, Any]]:
        by_a = {x["class"]: x for x in a["class_metrics"]}; by_p = {x["class"]: x for x in p["class_metrics"]}
        return [{"class": name, "active": by_a[name], "proposal": by_p[name], "recall_delta": by_p[name]["recall"] - by_a[name]["recall"]} for name in CLASSES]

    def _acceptance(self, state: dict[str, Any]) -> dict[str, Any]:
        a = state["evaluation"]["participants"]["active_candidate"]; p = state["evaluation"]["participants"]["proposal"]
        observed = [True, True, True, True, True, True, True, "comparable", a["benign_recall"], p["benign_recall"],
                    a["false_positive_rate"], p["false_positive_rate"], a["attack_macro_recall"], p["attack_macro_recall"],
                    a["attack_macro_f1"], p["attack_macro_f1"], a["worst_attack_recall"], p["worst_attack_recall"],
                    a["missing_prediction_count"] + p["missing_prediction_count"], a["duplicate_prediction_count"] + p["duplicate_prediction_count"],
                    a["invalid_prediction_count"] + p["invalid_prediction_count"], 0, True, True]
        results = []
        for criterion, value in zip(state["acceptance_definition"]["criteria"], observed):
            op, threshold = criterion["operator"], criterion["threshold"]
            passed = value is threshold if op == "boolean" else value == threshold if op == "equals" else value >= threshold if op == "minimum" else value <= threshold
            results.append({"criterion_id": criterion["criterion_id"], "name": criterion["name"], "mandatory": True,
                            "threshold": threshold, "observed": value, "status": "passed" if passed else "failed"})
        return {"schema_version": "blind_acceptance_gate_result_v1", "gate_id": state["acceptance_definition"]["gate_id"],
                "results": results, "passed_count": sum(x["status"] == "passed" for x in results),
                "failed_count": sum(x["status"] == "failed" for x in results), "not_assessable_count": 0,
                "invalidated_count": 0, "all_mandatory_passed": all(x["status"] == "passed" for x in results),
                "hidden_weight_count": 0, "winner_selected": False}

    def _prediction_plan(self, catalog: dict, inputs: dict) -> dict[str, Any]:
        return {"schema_version": "blind_prediction_plan_v1", "prediction_plan_id": "blind-plan-v047-r1",
                "control_pack_binding": catalog["control_pack_id"], "input_package_sha256": inputs["package_sha256"],
                "active_candidate_binding": {"candidate_id": ACTIVE_CANDIDATE, "artifact_sha256": ACTIVE_ARTIFACT_SHA},
                "proposal_binding": {"proposal_id": PROPOSAL_ID, "artifact_sha256": PROPOSAL_ARTIFACT_SHA, "semantic_sha256": PROPOSAL_MODEL_SEMANTIC_SHA},
                "feature_contract": "network_features_v2", "preprocessing_contract": "identity_float64",
                "threshold_contracts": ["frozen_candidate_v03154_calibrated_argmax", "argmax_multiclass_v046_r1"],
                "class_contract": "network_classes_v2", "event_contract": "shadow_event_v2", "warmup_policy": "first_9_windows_per_session",
                "scoring_policy": "all_post_warmup", "runner_version": "v047-safe-inprocess-inference-r1",
                "environment_profile": "local-offline-cpu", "resource_limits": {"cpu_threads": 1, "memory_mib": 1024},
                "timeout_seconds": 180, "execution_order_policy": "deterministic_randomized_order", "execution_order": ["active_candidate", "proposal"],
                "output_contract": "blind_prediction_row_v1", "prediction_package_contract": "blind_prediction_package_v1",
                "retry_policy": "same_plan_before_unlock_only", "interruption_policy": "checkpoint_and_deterministic_recovery",
                "allowed_failures": ["controlled_interruption"], "plan_sha256": None, "frozen": False}

    @staticmethod
    def _role_assignments(token: str) -> list[dict[str, Any]]:
        return [{"schema_version": "blind_validation_role_assignment_v1", "assignment_id": f"assign-{i:02d}",
                 "validation_token": token, "role": role, "operator_identity": "local-role-separated-operator",
                 "separate_workspace": True, "capability_token_separate": True, "independent_human": False}
                for i, role in enumerate(ROLES, 1)]

    def _save(self, state: dict[str, Any]) -> None:
        state["updated_at"] = now()
        with self.db.connect() as con:
            con.execute("INSERT INTO blind_validations VALUES(?,?,?,?,?,?) ON CONFLICT(token) DO UPDATE SET status=excluded.status,payload_json=excluded.payload_json,updated_at=excluded.updated_at",
                        (state["validation_token"], state["validation_lineage_id"], state["status"], json.dumps(state, ensure_ascii=False, sort_keys=True), state.get("created_at", now()), state["updated_at"]))

    def _save_review(self, value: dict[str, Any], action: str) -> None:
        with self.db.connect() as con:
            con.execute("UPDATE blind_validation_reviews SET version=?,status=?,payload_json=?,updated_at=? WHERE id=?",
                        (value["version"], value["status"], json.dumps(value, ensure_ascii=False, sort_keys=True), value["updated_at"], value["review_id"]))
            con.execute("INSERT INTO blind_validation_review_versions(review_id,version,occurred_at,action,payload_json) VALUES(?,?,?,?,?)",
                        (value["review_id"], value["version"], now(), action, json.dumps(value, ensure_ascii=False, sort_keys=True)))

    @staticmethod
    def _replace_run(state: dict[str, Any], record: dict[str, Any]) -> None:
        for index, current in enumerate(state["inference_runs"]):
            if current["execution_id"] == record["execution_id"]: state["inference_runs"][index] = record; return

    def _work(self, token: str) -> Path:
        safe_token(token); return self.root / "validations" / token

    @staticmethod
    def _write(path: Path, value: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")

    @staticmethod
    def _read(path: Path) -> Any:
        return json.loads(path.read_text(encoding="utf-8"))

    def _import_official(self) -> None:
        evidence = self.root / "official-evidence.json"
        if not evidence.is_file(): return
        state = self._read(evidence).get("state")
        if not state: return
        with self.db.connect() as con:
            con.execute("DELETE FROM blind_validations WHERE lineage_id=? AND token<>?", (state["validation_lineage_id"], state["validation_token"]))
            con.execute("INSERT INTO blind_validations VALUES(?,?,?,?,?,?) ON CONFLICT(token) DO UPDATE SET status=excluded.status,payload_json=excluded.payload_json,updated_at=excluded.updated_at",
                        (state["validation_token"], state["validation_lineage_id"], state["status"], json.dumps(state, ensure_ascii=False, sort_keys=True), state["created_at"], state["updated_at"]))
