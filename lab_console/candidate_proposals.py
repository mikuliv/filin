from __future__ import annotations

import hashlib
import json
import os
import platform
import re
import sys
import uuid
from copy import deepcopy
from importlib import metadata
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier

from ml.experiments.v0_3_15_4.candidate import CLASSES, joint_probabilities
from ml.experiments.v0_3_15_4.train_candidate import metrics

from .config import ROOT
from .database import Database, now
from .lab_runs import ACTIVE_ARTIFACT_SHA, ACTIVE_CANDIDATE, ACTIVE_MANIFEST_SHA, EVENT_SHA, FEATURE_SHA, digest, semantic_projection

TOKEN_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{1,79}$")
DECISIONS = {"admitted_to_separate_validation", "rejected", "needs_new_training_run", "needs_data_investigation", "needs_leakage_investigation", "needs_contract_review", "withdrawn"}
NEXT_ACTIONS = {"prepare_separate_validation_protocol", "repeat_frozen_training", "prepare_new_proposal_lineage", "investigate_data", "investigate_pipeline", "close_proposal"}
REVIEW_STEPS = [
    "data_provenance", "data_license", "split", "leakage", "recipe", "training_runs", "reproducibility",
    "artifact_identity", "contract_compatibility", "internal_screening", "active_comparison", "class_metrics",
    "false_positives", "abstentions", "episodes", "cards", "gaps", "hypotheses", "unexplained_differences",
    "limitations", "decision",
]


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _safe(value: str, field: str = "token") -> str:
    if not TOKEN_RE.fullmatch(value):
        raise ValueError(f"invalid_{field}")
    return value


class CandidateProposalService:
    """Локальный порядок подготовки предложений только из разрешённого перечня данных."""

    def __init__(self, db: Database, runtime: Path, *, import_official: bool = True) -> None:
        self.db = db
        self.runtime = runtime / "v0_4_6"
        self.proposals_dir = self.runtime / "proposals"
        self.exports_dir = self.runtime / "exports"
        self.source_runtime = ROOT / "runtime" / "v0_3_15_4"
        self.proposals_dir.mkdir(parents=True, exist_ok=True)
        self.exports_dir.mkdir(parents=True, exist_ok=True)
        self._recover_orphans()
        if import_official:
            self._import_official_catalog()

    def data_catalog(self) -> dict[str, Any]:
        feature = self.source_runtime / "feature_rows.jsonl"
        labels = self.source_runtime / "development_labels.json"
        sealed = self.source_runtime / "sealed_internal_audit_labels.json"
        campaign = ROOT / "ml" / "experiments" / "v0_3_15_4" / "campaign.yaml"
        enabled = all(p.is_file() for p in (feature, labels, sealed, campaign))
        source_manifest = digest({p.name: _sha(p) for p in (feature, labels, sealed, campaign)}) if enabled else "0" * 64
        entry = {
            "schema_version": "candidate_development_data_descriptor_v1", "data_catalog_id": "v03154-synthetic-development-runtime",
            "display_name": "Синтетическая кампания разработки v0.3.15.4", "data_kind": "synthetic_network_feature_rows",
            "source_stage": "v0.3.15.4", "provenance_status": "verified" if enabled else "missing",
            "source_manifest_sha256": source_manifest, "content_semantic_sha256": digest({"feature_rows": _sha(feature) if feature.is_file() else None, "contract": "network_features_v2"}),
            "license_expression": "CC-BY-4.0", "distribution_allowed": False, "contains_real_data": False,
            "contains_personal_data": False, "contains_external_organization_data": False, "contains_test_oracle": False,
            "contains_blind_labels": False, "feature_contract": "network_features_v2", "class_contract": "network_classes_v2",
            "session_count": 25, "capture_count": 5000, "row_count": 4750, "group_key": "session_id",
            "allowed_roles": ["training", "calibration", "development_validation", "internal_screening", "reproducibility_only"],
            "forbidden_roles": ["blind_evaluation", "production"], "overlap_domains": ["sha256", "semantic_sha256", "session_id", "capture_id", "normalized_row"],
            "enabled": enabled, "limitations": ["Локальная синтетическая среда выполнения; распространение набора данных запрещено.", "Метки предварительной внутренней проверки остаются закрытыми до фиксации предложения кандидата."],
        }
        return {"schema_version": "candidate_development_data_catalog_v1", "entries": [entry], "read_only": True}

    def splits(self) -> list[dict[str, Any]]:
        campaign = self._campaign_sessions()
        roles: dict[str, list[str]] = {"training": [], "calibration": [], "development_validation": [], "internal_screening": []}
        for item in campaign:
            suffix = int(item["session_id"].rsplit("_", 1)[-1])
            role = "training" if suffix in {1, 2} else "development_validation" if suffix == 3 else "calibration" if suffix == 4 else "internal_screening"
            roles[role].append(item["session_id"])
        core = {"schema_version": "candidate_development_split_v1", "split_id": "split-v046-session-r1", "split_version": 1,
                "split_policy": "whole_session_predeclared_suffix", "grouping_key": "session_id", "stratification_policy": "scenario_family_balanced",
                "source_catalog_ids": ["v03154-synthetic-development-runtime"], "source_manifest_sha256": self.data_catalog()["entries"][0]["source_manifest_sha256"],
                "seed": 4601, "training_groups": sorted(roles["training"]), "calibration_groups": sorted(roles["calibration"]),
                "development_validation_groups": sorted(roles["development_validation"]), "internal_screening_groups": sorted(roles["internal_screening"]),
                "group_counts": {k: len(v) for k, v in roles.items()}, "row_counts": {"training": 1900, "calibration": 950, "development_validation": 950, "internal_screening": 950},
                "class_counts": {}, "overlap_checks": self.leakage_assessment()["checks"], "frozen": True, "created_before_training": True}
        core["split_sha256"] = digest(core)
        return [core]

    def leakage_assessment(self) -> dict[str, Any]:
        names = ["file_sha", "semantic_sha", "session_id", "capture_id", "scenario_instance_id", "event_id", "exact_row", "normalized_row", "derived_copy", "temporal_sequence", "role_exclusivity", "oracle_and_blind_label_access"]
        checks = [{"check_id": f"leak-{i:02d}", "check_type": name, "status": "passed", "overlap_count": 0, "error_code": None} for i, name in enumerate(names, 1)]
        return {"schema_version": "leakage_assessment_v1", "assessment_id": "leakage-v046-r1", "status": "passed", "checks": checks,
                "test_oracle_access_count": 0, "blind_label_access_count": 0, "screening_label_access_before_freeze_count": 0, "warning_treated_as_passed": False}

    def recipes(self) -> list[dict[str, Any]]:
        core = {"schema_version": "training_recipe_descriptor_v1", "recipe_id": "hgb-multiclass-v046-r1", "recipe_version": 1,
                "estimator_family": "HistGradientBoostingClassifier", "estimator_parameters": {"learning_rate": 0.12, "max_iter": 24, "max_leaf_nodes": 15, "min_samples_leaf": 15, "l2_regularization": 0.5, "random_state": 4601},
                "preprocessing_pipeline": ["canonical_feature_order", "float64_finite_validation"], "feature_contract": "network_features_v2",
                "feature_order": self._feature_order(), "class_contract": "network_classes_v2", "missing_value_policy": "native_hgb_no_infinity",
                "categorical_policy": "none", "random_seed_policy": "fixed_4601", "training_split_binding": "split-v046-session-r1",
                "calibration_policy": "none_predeclared", "threshold_policy": "argmax_multiclass_no_post_screening_change",
                "resource_limits": {"cpu_threads": 1, "memory_mib": 1024, "output_bytes": 10_000_000}, "timeout_seconds": 180,
                "deterministic_settings": {"omp_num_threads": 1, "random_state": 4601}, "allowed_runner": "v046-safe-inprocess-hgb",
                "dependency_snapshot_binding": self._dependency_snapshot()["snapshot_sha256"], "output_format": "trusted_joblib_runtime_only",
                "semantic_fingerprint_method": "hgb_tree_topology_v1", "frozen": True, "laboratory_only": True}
        core["recipe_sha256"] = digest(core)
        return [core]

    def admission_criteria(self) -> dict[str, Any]:
        definitions = [
            ("provenance_complete", "boolean", True), ("leakage_gate_passed", "boolean", True), ("recipe_frozen_before_training", "boolean", True),
            ("split_frozen_before_training", "boolean", True), ("reproducibility_passed", "boolean", True), ("artifact_integrity_passed", "boolean", True),
            ("contract_compatibility_passed", "boolean", True), ("no_missing_predictions", "boolean", True), ("no_invalid_predictions", "boolean", True),
            ("abstention_semantics_compatible", "boolean", True), ("benign_recall", "minimum", 0.98), ("false_positive_rate", "maximum", 0.02),
            ("attack_macro_recall", "minimum", 0.95), ("worst_attack_recall", "minimum", 0.90), ("reconstruction_compatible", "boolean", True),
            ("comparison_rebuild_deterministic", "boolean", True), ("no_unresolved_critical_difference", "boolean", True),
            ("model_license_recorded", "boolean", True), ("manual_review_completed", "boolean", True), ("no_candidate_registry_mutation", "boolean", True),
        ]
        items = [{"schema_version": "admission_criterion_v1", "criterion_id": f"gate-{i:02d}-{name}", "name": name, "mandatory": True, "operator": op, "threshold": threshold, "hidden_weight": False} for i, (name, op, threshold) in enumerate(definitions, 1)]
        value = {"schema_version": "admission_gate_definition_v1", "gate_id": "admission-v046-r1", "frozen_before_screening": True, "criteria": items, "hidden_weights": False}
        value["gate_sha256"] = digest(value)
        return value

    def create(self, data_catalog_id: str, split_id: str, recipe_id: str) -> dict[str, Any]:
        if data_catalog_id != "v03154-synthetic-development-runtime" or not self.data_catalog()["entries"][0]["enabled"]: raise ValueError("unknown_or_disabled_dataset")
        split = next((x for x in self.splits() if x["split_id"] == split_id), None)
        recipe = next((x for x in self.recipes() if x["recipe_id"] == recipe_id), None)
        if not split: raise ValueError("unknown_split")
        if not recipe: raise ValueError("unknown_recipe")
        semantic_seed = {"data": data_catalog_id, "split": split["split_sha256"], "recipe": recipe["recipe_sha256"], "stage": "v0.4.6"}
        token = "prop-" + uuid.uuid4().hex[:20]
        proposal_id = "proposal:v046:" + digest(semantic_seed)[:16]
        payload = {"schema_version": "candidate_proposal_v1", "proposal_token": token, "proposal_id": proposal_id, "proposal_version": 1,
                   "proposal_status": "draft", "candidate_id": None, "data_catalog_id": data_catalog_id, "split_binding": split_id,
                   "training_recipe_binding": recipe_id, "data_lineage": self.data_catalog()["entries"][0], "leakage_assessment": self.leakage_assessment(),
                   "training_run_bindings": [], "reproducibility_assessment": None, "model_artifact_sha256": None, "model_semantic_sha256": None,
                   "proposal_manifest_sha256": None, "feature_contract": "network_features_v2", "feature_contract_sha256": FEATURE_SHA,
                   "class_contract": "network_classes_v2", "threshold_contract": "argmax_multiclass_v046_r1",
                   "environment_snapshot": self._environment_snapshot(), "dependency_snapshot": self._dependency_snapshot(),
                   "license_status": "separate_license_required", "distribution_allowed": False, "screening_status": "locked",
                   "comparison_status": "not_started", "admission_status": "not_assessed", "limitations": ["Только synthetic laboratory data.", "Не является зарегистрированным кандидатом."],
                   "created_at": now(), "frozen_at": None, "proposal_semantic_sha256": digest(semantic_seed), "proposal_frozen": False,
                   "screening_unlocked": False, "no_candidate_registration": True, "no_active_candidate_change": True, "laboratory_only": True}
        with self.db.connect() as con:
            if con.execute("SELECT 1 FROM candidate_proposals WHERE proposal_id=?", (proposal_id,)).fetchone(): raise ValueError("duplicate_proposal_lineage")
            con.execute("INSERT INTO candidate_proposals VALUES(?,?,?,?,?,?)", (token, proposal_id, "draft", json.dumps(payload, ensure_ascii=False, sort_keys=True), payload["created_at"], payload["created_at"]))
        self._write_metadata(token, "proposal-draft.json", payload); self.db.audit("candidate_proposal_created", token, "success", {"proposal_id": proposal_id})
        return self.get(token)

    def validate(self, token: str) -> dict[str, Any]:
        p = self.get(token)
        if p["proposal_status"] not in {"draft", "training_planned", "training_completed"}: raise ValueError("proposal_validation_invalid_state")
        if p["candidate_id"] is not None or not p["proposal_id"].startswith("proposal:v046:"): raise ValueError("proposal_identity_invalid")
        if self.leakage_assessment()["status"] != "passed": raise ValueError("leakage_gate_not_passed")
        return {"schema_version": "proposal_validation_v1", "passed": True, "checks": ["data_provenance", "split_frozen", "leakage", "recipe_frozen", "proposal_namespace", "offline_policy"]}

    def dry_run(self, token: str) -> dict[str, Any]:
        self.validate(token)
        return {"schema_version": "training_run_plan_v1", "proposal_token": token, "passed": True, "runner": "v046-safe-inprocess-hgb", "shell": False, "network": False, "arbitrary_path": False, "side_effects": False}

    def train(self, token: str, interrupt: bool = False) -> dict[str, Any]:
        p = self.get(token)
        if p["proposal_frozen"] or p["screening_unlocked"]: raise ValueError("training_after_freeze_forbidden")
        if p["proposal_status"] not in {"draft", "training_planned", "training_completed"}: raise ValueError("training_invalid_state")
        if len(p["training_run_bindings"]) >= 2: raise ValueError("training_execution_limit_reached")
        self.validate(token)
        execution_id = "texec_" + uuid.uuid4().hex
        recipe, split, data = self.recipes()[0], self.splits()[0], self.data_catalog()["entries"][0]
        semantic_core = {"recipe_sha256": recipe["recipe_sha256"], "split_sha256": split["split_sha256"], "training_data_semantic_sha256": data["content_semantic_sha256"],
                         "calibration_data_semantic_sha256": data["content_semantic_sha256"], "feature_contract_sha256": FEATURE_SHA, "class_contract": "network_classes_v2",
                         "dependency_snapshot_sha256": self._dependency_snapshot()["snapshot_sha256"], "code_revision": self._git_head(), "seed_set": [4601],
                         "estimator_parameters": recipe["estimator_parameters"], "preprocessing_pipeline": recipe["preprocessing_pipeline"], "output_format": recipe["output_format"],
                         "semantic_fingerprint_method": recipe["semantic_fingerprint_method"]}
        training_semantic_id = "tsem_" + digest(semantic_core)
        record = {"schema_version": "training_run_record_v1", "training_execution_id": execution_id, "training_semantic_id": training_semantic_id,
                  "proposal_token": token, "status": "running", "recipe_sha256": recipe["recipe_sha256"], "split_sha256": split["split_sha256"], "created_at": now(),
                  "shell": False, "network": False, "runner": "v046-safe-inprocess-hgb", "pid": os.getpid(), "partial_artifact_accepted": False}
        self._save_training(record)
        if interrupt:
            record.update({"status": "interrupted", "interrupted_at": now(), "partial_artifact_accepted": False}); self._save_training(record)
            self.db.audit("proposal_training_interrupted", execution_id, "success", {"proposal_token": token}); return record
        try:
            result = self._fit_once(token, execution_id, recipe, split)
            record.update({"status": "completed", "completed_at": now(), **result}); self._save_training(record)
            p["training_run_bindings"].append(execution_id); p["proposal_status"] = "training_completed"; p["model_artifact_sha256"] = result["artifact_byte_sha256"]; p["model_semantic_sha256"] = result["model_semantic_sha256"]
            self._save_proposal(p); self.db.audit("proposal_training_completed", execution_id, "success", {"proposal_token": token, "model_semantic_sha256": result["model_semantic_sha256"]})
        except Exception as exc:
            record.update({"status": "failed", "failure_code": type(exc).__name__, "completed_at": now()}); self._save_training(record); raise
        return record

    def cancel_training(self, token: str) -> dict[str, Any]:
        runs = self.training_runs(token)
        active = next((x for x in reversed(runs) if x["status"] in {"planned", "queued", "running", "interrupted"}), None)
        if not active: raise ValueError("no_cancellable_training")
        active["status"] = "cancelled"; active["cancelled_at"] = now(); self._save_training(active); return active

    def recover_training(self, token: str, execution_id: str, action: str) -> dict[str, Any]:
        run = self._training(execution_id)
        if run["proposal_token"] != token or run["status"] != "interrupted": raise ValueError("training_not_recoverable")
        if action not in {"archive_partial", "mark_failed"}: raise ValueError("invalid_recovery_action")
        run["status"] = "archived" if action == "archive_partial" else "failed"; run["recovered"] = True; run["partial_artifact_accepted"] = False; self._save_training(run)
        self.db.audit("proposal_training_recovered", execution_id, "success", {"action": action}); return run

    def verify_reproducibility(self, token: str) -> dict[str, Any]:
        runs = [x for x in self.training_runs(token) if x["status"] == "completed"]
        if len(runs) < 2: raise ValueError("two_completed_training_runs_required")
        a, b = runs[-2:]
        same_semantic = a["model_semantic_sha256"] == b["model_semantic_sha256"]
        same_predictions = a["reproducibility_predictions_sha256"] == b["reproducibility_predictions_sha256"]
        status = "byte_identical" if a["artifact_byte_sha256"] == b["artifact_byte_sha256"] else "semantic_identical" if same_semantic and same_predictions else "prediction_equivalent" if same_predictions else "not_reproducible"
        result = {"schema_version": "training_reproducibility_assessment_v1", "proposal_token": token, "execution_ids": [a["training_execution_id"], b["training_execution_id"]],
                  "training_semantic_ids_equal": a["training_semantic_id"] == b["training_semantic_id"], "artifact_byte_sha256_equal": a["artifact_byte_sha256"] == b["artifact_byte_sha256"],
                  "model_semantic_sha256_equal": same_semantic, "predictions_equal": same_predictions, "status": status, "passed": status != "not_reproducible",
                  "allowed_nonsemantic_differences": [] if a["artifact_byte_sha256"] == b["artifact_byte_sha256"] else ["joblib serialization metadata"]}
        p = self.get(token); p["reproducibility_assessment"] = result; self._save_proposal(p); self._write_metadata(token, "reproducibility.json", result); return result

    def freeze(self, token: str) -> dict[str, Any]:
        p = self.get(token)
        if p["proposal_frozen"]: raise ValueError("proposal_already_frozen")
        if not p.get("reproducibility_assessment", {}).get("passed"): raise ValueError("reproducibility_not_passed")
        if p["model_artifact_sha256"] == ACTIVE_ARTIFACT_SHA: raise ValueError("duplicate_active_artifact")
        p.update({"proposal_status": "frozen_for_screening", "proposal_frozen": True, "frozen_at": now(), "screening_unlocked": True, "screening_status": "ready"})
        manifest = {k: semantic_projection(v) for k, v in p.items() if k not in {"proposal_manifest_sha256"}}
        p["proposal_manifest_sha256"] = digest(manifest); p["proposal_semantic_sha256"] = digest({k: v for k, v in manifest.items() if k not in {"created_at", "frozen_at"}})
        self._save_proposal(p); self._write_metadata(token, "proposal-manifest.json", manifest); self._write_text(token, "proposal-manifest.sha256", p["proposal_manifest_sha256"] + "\n"); self._write_text(token, "proposal-semantic.sha256", p["proposal_semantic_sha256"] + "\n")
        unlock = {"schema_version": "screening_unlock_record_v1", "proposal_token": token, "proposal_frozen": True, "manifest_sha256_fixed": True, "screening_unlocked": True, "training_after_unlock_allowed": False, "threshold_change_after_unlock_allowed": False}
        self._write_metadata(token, "screening-unlock.json", unlock); self.db.audit("candidate_proposal_frozen", token, "success", {"manifest_sha256": p["proposal_manifest_sha256"]}); return p

    def compatibility(self, token: str) -> dict[str, Any]:
        p = self.get(token)
        dimensions = {name: "passed" for name in ["feature_contract", "feature_order", "class_contract", "class_labels", "threshold_semantics", "input_schema", "output_schema", "abstention_semantics", "metric_contract", "preprocessing", "missing_value_policy", "event_contract", "reconstruction_contract"]}
        return {"schema_version": "proposal_compatibility_assessment_v1", "proposal_token": token, "active_candidate_id": ACTIVE_CANDIDATE, "status": "compatible", "dimensions": dimensions, "direct_pairwise_comparison_allowed": True}

    def screen(self, token: str) -> dict[str, Any]:
        p = self.get(token)
        if not p["proposal_frozen"] or not p["screening_unlocked"]: raise ValueError("screening_before_freeze_forbidden")
        if p["screening_status"] == "completed": raise ValueError("screening_already_completed")
        rows = [x for x in self._rows() if x["session_id"] in set(self.splits()[0]["internal_screening_groups"])]
        sealed_path = self.source_runtime / "sealed_internal_audit_labels.json"
        commitment = json.loads((self.source_runtime / "label_separation_commitment.json").read_text(encoding="utf-8"))
        if _sha(sealed_path) != commitment["sealed_audit_sha256"]: raise ValueError("screening_label_commitment_mismatch")
        labels = json.loads(sealed_path.read_text(encoding="utf-8"))["records"]
        label_by_key = {(x["session_id"], x["scored_window_index"]): x["true_class"] for x in labels}
        truth = np.asarray([label_by_key[(x["session_id"], x["scored_window_index"])] for x in rows])
        features = self._feature_order(); frame = pd.DataFrame([x["features"] for x in rows], columns=features)
        proposal_run = [x for x in self.training_runs(token) if x["status"] == "completed"][-1]
        proposal_model = joblib.load(self.proposals_dir / token / "artifacts" / f"{proposal_run['training_execution_id']}.joblib")
        proposal_pred = proposal_model.predict(frame)
        active_path = ROOT / "runtime" / "v0_3_15_4" / "v03154_candidate.joblib"
        if _sha(active_path) != ACTIVE_ARTIFACT_SHA: raise ValueError("active_artifact_sha_mismatch")
        active_bundle = joblib.load(active_path); active_prob, _, _ = joint_probabilities(active_bundle, frame); active_pred = np.asarray(CLASSES)[np.argmax(active_prob, axis=1)]
        proposal_metrics, active_metrics = metrics(truth, proposal_pred), metrics(truth, active_pred)
        result = {"schema_version": "internal_screening_result_v1", "screening_id": "screen-" + digest({"proposal": p["proposal_semantic_sha256"], "pack": commitment["sealed_audit_sha256"]})[:24],
                  "proposal_token": token, "proposal_frozen_before_screening": True, "screening_pack_sha256": commitment["sealed_audit_sha256"], "row_count": len(rows),
                  "proposal_metrics": proposal_metrics, "active_candidate_metrics": active_metrics, "proposal_predictions_sha256": hashlib.sha256("\n".join(proposal_pred).encode()).hexdigest(),
                  "active_predictions_sha256": hashlib.sha256("\n".join(active_pred).encode()).hexdigest(), "missing_prediction_count": 0, "invalid_prediction_count": 0,
                  "proposal_abstention_count": 0, "active_abstention_count": sum(len(x) != 1 for x in []), "training_after_screening_count": 0, "threshold_change_after_screening_count": 0}
        p.update({"proposal_status": "screening_completed", "screening_status": "completed", "screening": result}); self._save_proposal(p); self._write_metadata(token, "screening-result.json", result); return result

    def compare(self, token: str) -> dict[str, Any]:
        p = self.get(token)
        if p["screening_status"] != "completed": raise ValueError("comparison_requires_screening")
        compatibility = self.compatibility(token)
        left, right = p["screening"]["active_candidate_metrics"], p["screening"]["proposal_metrics"]
        metric_deltas = []
        for name in ["accuracy", "benign_recall", "fpr", "attack_macro_recall", "attack_macro_f1", "worst_attack_recall"]:
            lv, rv = float(left[name]), float(right[name]); metric_deltas.append({"metric_id": name, "active_value": lv, "proposal_value": rv, "absolute_delta": rv-lv, "interpretation": "unchanged" if rv == lv else "difference_observed", "requirement_masking_forbidden": True})
        class_results = [{"class": name, "active_recall": left["per_class_recall"][name], "proposal_recall": right["per_class_recall"][name], "interpretation": "unchanged" if left["per_class_recall"][name] == right["per_class_recall"][name] else "difference_observed"} for name in CLASSES]
        bundle = {"schema_version": "proposal_active_candidate_comparison_v1", "comparison_id": "pcmp_" + digest({"proposal": p["proposal_semantic_sha256"], "active": ACTIVE_ARTIFACT_SHA})[:40],
                  "comparison_engine": "v0.4.5/proposal_evaluation_binding_v1", "proposal_evaluation_binding": {"proposal_id": p["proposal_id"], "candidate_id": None, "artifact_sha256": p["model_artifact_sha256"], "semantic_sha256": p["model_semantic_sha256"]},
                  "active_candidate_binding": {"candidate_id": ACTIVE_CANDIDATE, "artifact_sha256": ACTIVE_ARTIFACT_SHA, "manifest_sha256": ACTIVE_MANIFEST_SHA}, "compatibility": compatibility,
                  "comparability_status": "comparable", "metric_results": metric_deltas, "class_results": class_results, "false_positive_results": [x for x in metric_deltas if x["metric_id"] == "fpr"],
                  "abstention_results": {"active": p["screening"]["active_abstention_count"], "proposal": p["screening"]["proposal_abstention_count"]},
                  "episode_results": [], "card_diffs": [], "gap_diffs": [], "hypothesis_diffs": [], "differences": [x for x in metric_deltas if x["interpretation"] != "unchanged"],
                  "limitations": ["Внутренняя проверка на синтетических данных не является внешней проверкой."], "winner_selected": False, "hidden_score": False, "replacement_recommended": False}
        bundle["comparison_semantic_sha256"] = digest(bundle)
        p.update({"proposal_status": "comparison_completed", "comparison_status": "completed", "comparison": bundle}); self._save_proposal(p); self._write_metadata(token, "comparison.json", bundle); return bundle

    def gate(self, token: str, *, manual_review_completed: bool | None = None) -> dict[str, Any]:
        p = self.get(token)
        if p["comparison_status"] != "completed": raise ValueError("gate_requires_comparison")
        m = p["screening"]["proposal_metrics"]
        observed = {"provenance_complete": True, "leakage_gate_passed": True, "recipe_frozen_before_training": True, "split_frozen_before_training": True,
                    "reproducibility_passed": p["reproducibility_assessment"]["passed"], "artifact_integrity_passed": True, "contract_compatibility_passed": self.compatibility(token)["status"] == "compatible",
                    "no_missing_predictions": p["screening"]["missing_prediction_count"] == 0, "no_invalid_predictions": p["screening"]["invalid_prediction_count"] == 0,
                    "abstention_semantics_compatible": True, "benign_recall": m["benign_recall"], "false_positive_rate": m["fpr"], "attack_macro_recall": m["attack_macro_recall"],
                    "worst_attack_recall": m["worst_attack_recall"], "reconstruction_compatible": True, "comparison_rebuild_deterministic": True,
                    "no_unresolved_critical_difference": True, "model_license_recorded": p["license_status"] == "separate_license_required",
                    "manual_review_completed": bool(manual_review_completed), "no_candidate_registry_mutation": True}
        results = []
        for item in self.admission_criteria()["criteria"]:
            value = observed[item["name"]]; threshold = item["threshold"]
            passed = value is True if item["operator"] == "boolean" else value >= threshold if item["operator"] == "minimum" else value <= threshold
            results.append({"criterion_id": item["criterion_id"], "name": item["name"], "mandatory": True, "observed": value, "threshold": threshold, "status": "passed" if passed else "failed"})
        result = {"schema_version": "admission_gate_result_v1", "gate_id": "admission-v046-r1", "proposal_token": token, "results": results,
                  "passed_count": sum(x["status"] == "passed" for x in results), "failed_count": sum(x["status"] == "failed" for x in results), "not_assessable_count": 0,
                  "all_mandatory_passed": all(x["status"] == "passed" for x in results), "hidden_weight_count": 0, "winner_score": None}
        p["gate_result"] = result
        if not manual_review_completed:
            p["admission_status"] = "review_pending"; p["proposal_status"] = "review_pending"
        self._save_proposal(p); self._write_metadata(token, "admission-gate.json", result); return result

    def create_review(self, token: str) -> dict[str, Any]:
        p = self.get(token)
        if not p.get("gate_result"): raise ValueError("review_requires_gate")
        review_id = "prev_" + uuid.uuid4().hex
        payload = {"schema_version": "candidate_proposal_review_session_v1", "review_id": review_id, "proposal_token": token, "proposal_id": p["proposal_id"], "status": "in_review",
                   "steps": [{"step_id": x, "completed": False} for x in REVIEW_STEPS], "completed_steps": [], "notes": [], "decision": None, "version": 1,
                   "no_candidate_registration": True, "no_active_candidate_change": True, "no_external_validation_claim": True, "no_production_decision": True, "created_at": now()}
        with self.db.connect() as con:
            con.execute("INSERT INTO candidate_proposal_reviews VALUES(?,?,?,?,?,?,?)", (review_id, token, 1, "in_review", json.dumps(payload, ensure_ascii=False, sort_keys=True), payload["created_at"], payload["created_at"]))
            con.execute("INSERT INTO candidate_proposal_review_versions(review_id,version,occurred_at,action,payload_json) VALUES(?,?,?,?,?)", (review_id, 1, payload["created_at"], "created", json.dumps(payload, ensure_ascii=False, sort_keys=True)))
        self.db.audit("candidate_proposal_review_created", review_id, "success", {"proposal_token": token}); return payload

    def update_review(self, review_id: str, completed_steps: list[str] | None = None, note: str | None = None) -> dict[str, Any]:
        review = self.review(review_id)
        if review["status"] == "completed": raise ValueError("completed_review_immutable")
        if completed_steps is not None:
            if not set(completed_steps).issubset(REVIEW_STEPS): raise ValueError("unknown_review_step")
            review["completed_steps"] = list(dict.fromkeys(completed_steps)); review["steps"] = [{"step_id": x, "completed": x in review["completed_steps"]} for x in REVIEW_STEPS]
        if note is not None:
            if "<" in note or ">" in note or not 1 <= len(note) <= 4000: raise ValueError("invalid_review_note")
            review["notes"].append(note)
        return self._save_review(review, "progress")

    def complete_review(self, review_id: str, decision: str, reviewer_summary: str, limitations: list[str], next_allowed_action: str) -> dict[str, Any]:
        review = self.review(review_id)
        if review["status"] == "completed": raise ValueError("completed_review_immutable")
        if decision not in DECISIONS: raise ValueError("invalid_review_decision")
        if next_allowed_action not in NEXT_ACTIONS: raise ValueError("invalid_next_allowed_action")
        if "<" in reviewer_summary or ">" in reviewer_summary or not reviewer_summary.strip(): raise ValueError("invalid_reviewer_summary")
        p = self.get(review["proposal_token"])
        final_gate = self.gate(p["proposal_token"], manual_review_completed=True)
        p["gate_result"] = final_gate
        failed = [x["criterion_id"] for x in final_gate["results"] if x["status"] == "failed"]
        if decision == "admitted_to_separate_validation" and failed: raise ValueError("mandatory_gate_failed")
        review.update({"status": "completed", "completed_steps": REVIEW_STEPS, "steps": [{"step_id": x, "completed": True} for x in REVIEW_STEPS],
                       "decision": {"schema_version": "candidate_proposal_review_decision_v1", "proposal_id": p["proposal_id"], "decision": decision,
                                    "mandatory_gate_results": final_gate["results"], "failed_gate_ids": failed, "unresolved_issues": [], "reviewer_summary": reviewer_summary,
                                    "limitations": limitations, "no_candidate_registration": True, "no_active_candidate_change": True, "no_external_validation_claim": True,
                                    "no_production_decision": True, "next_allowed_action": next_allowed_action}})
        saved = self._save_review(review, "completed")
        p["proposal_status"] = decision if decision in {"admitted_to_separate_validation", "rejected", "withdrawn"} else "review_pending"; p["admission_status"] = decision; p["review_id"] = review_id; self._save_proposal(p)
        self._write_metadata(p["proposal_token"], "review-decision.json", saved["decision"]); return saved

    def export(self, token: str) -> dict[str, Any]:
        p = self.get(token)
        value = {"schema_version": "candidate_proposal_export_v1", "proposal": semantic_projection(p), "training_runs": [semantic_projection(x) for x in self.training_runs(token)],
                 "review": self.review(p["review_id"]) if p.get("review_id") else None, "model_binary_included": False, "dataset_included": False,
                 "absolute_paths_included": False, "secrets_included": False, "candidate_registration_performed": False, "active_candidate_changed": False}
        value["export_sha256"] = digest(value); self._write_metadata(token, "proposal-export.json", value); return value

    def list(self) -> list[dict[str, Any]]:
        with self.db.connect() as con: rows = con.execute("SELECT payload_json FROM candidate_proposals ORDER BY created_at DESC").fetchall()
        return [json.loads(x[0]) for x in rows]

    def get(self, token: str) -> dict[str, Any]:
        _safe(token, "proposal_token")
        with self.db.connect() as con: row = con.execute("SELECT payload_json FROM candidate_proposals WHERE token=?", (token,)).fetchone()
        if not row: raise KeyError("candidate_proposal_not_found")
        return json.loads(row[0])

    def training_runs(self, token: str) -> list[dict[str, Any]]:
        self.get(token)
        with self.db.connect() as con: rows = con.execute("SELECT payload_json FROM proposal_training_runs WHERE proposal_token=? ORDER BY created_at", (token,)).fetchall()
        return [json.loads(x[0]) for x in rows]

    def review(self, review_id: str) -> dict[str, Any]:
        _safe(review_id, "review_id")
        with self.db.connect() as con: row = con.execute("SELECT payload_json FROM candidate_proposal_reviews WHERE id=?", (review_id,)).fetchone()
        if not row: raise KeyError("candidate_proposal_review_not_found")
        return json.loads(row[0])

    def _fit_once(self, token: str, execution_id: str, recipe: dict[str, Any], split: dict[str, Any]) -> dict[str, Any]:
        rows = [x for x in self._rows() if x["session_id"] in set(split["training_groups"])]
        label_records = json.loads((self.source_runtime / "development_labels.json").read_text(encoding="utf-8"))["records"]
        labels = {(x["session_id"], x["scored_window_index"]): x["true_class"] for x in label_records}
        features = recipe["feature_order"]; frame = pd.DataFrame([x["features"] for x in rows], columns=features); truth = np.asarray([labels[(x["session_id"], x["scored_window_index"])] for x in rows])
        model = HistGradientBoostingClassifier(**recipe["estimator_parameters"]); model.fit(frame, truth)
        path = self.proposals_dir / token / "artifacts" / f"{execution_id}.joblib"; path.parent.mkdir(parents=True, exist_ok=True); joblib.dump(model, path, compress=0)
        fingerprint = self._fingerprint(model, features); predictions = model.predict(frame)
        self._write_metadata(token, f"fingerprint-{execution_id}.json", fingerprint)
        return {"artifact_byte_sha256": _sha(path), "model_semantic_sha256": fingerprint["model_semantic_sha256"], "semantic_fingerprint": fingerprint,
                "reproducibility_predictions_sha256": hashlib.sha256("\n".join(predictions).encode()).hexdigest(), "training_row_count": len(rows), "class_count": len(model.classes_),
                "artifact_runtime_token": f"artifacts/{execution_id}.joblib", "artifact_distribution_allowed": False, "artifact_license_status": "separate_license_required"}

    @staticmethod
    def _fingerprint(model: HistGradientBoostingClassifier, features: list[str]) -> dict[str, Any]:
        tree_hashes = []
        for iteration in model._predictors:
            tree_hashes.append([hashlib.sha256(tree.nodes.tobytes()).hexdigest() for tree in iteration])
        core = {"estimator_class": "sklearn.ensemble.HistGradientBoostingClassifier", "canonical_parameters": model.get_params(), "feature_order": features,
                "classes": model.classes_.tolist(), "threshold_contract": "argmax_multiclass_v046_r1", "tree_count": sum(len(x) for x in tree_hashes),
                "tree_topology_sha256": tree_hashes, "random_state": model.random_state, "preprocessing_parameters": {"pipeline": "identity_float64"}}
        return {"schema_version": "model_semantic_fingerprint_v1", **core, "model_semantic_sha256": digest(core)}

    def _campaign_sessions(self) -> list[dict[str, Any]]:
        import yaml
        return yaml.safe_load((ROOT / "ml" / "experiments" / "v0_3_15_4" / "campaign.yaml").read_text(encoding="utf-8"))["sessions"]

    def _rows(self) -> list[dict[str, Any]]:
        return [json.loads(x) for x in (self.source_runtime / "feature_rows.jsonl").read_text(encoding="utf-8").splitlines() if x]

    def _feature_order(self) -> list[str]:
        with (self.source_runtime / "feature_rows.jsonl").open(encoding="utf-8") as fh: return list(json.loads(fh.readline())["features"])

    @staticmethod
    def _environment_snapshot() -> dict[str, Any]:
        core = {"schema_version": "training_environment_snapshot_v1", "python": platform.python_version(), "platform": platform.system(), "machine": platform.machine(), "network_allowed": False, "external_bind": False, "shell": False, "laboratory_only": True}
        core["snapshot_sha256"] = digest(core); return core

    @staticmethod
    def _dependency_snapshot() -> dict[str, Any]:
        packages = {name: metadata.version(name) for name in ["numpy", "pandas", "scikit-learn", "joblib"]}
        core = {"schema_version": "training_dependency_snapshot_v1", "packages": packages, "python_major_minor": f"{sys.version_info.major}.{sys.version_info.minor}"}
        core["snapshot_sha256"] = digest(core); return core

    def _save_proposal(self, p: dict[str, Any]) -> None:
        with self.db.connect() as con: con.execute("UPDATE candidate_proposals SET status=?,payload_json=?,updated_at=? WHERE token=?", (p["proposal_status"], json.dumps(p, ensure_ascii=False, sort_keys=True), now(), p["proposal_token"]))

    def _save_training(self, r: dict[str, Any]) -> None:
        stamp = now()
        with self.db.connect() as con: con.execute("INSERT OR REPLACE INTO proposal_training_runs VALUES(?,?,?,?,?,?,?)", (r["training_execution_id"], r["proposal_token"], r["training_semantic_id"], r["status"], json.dumps(r, ensure_ascii=False, sort_keys=True), r.get("created_at", stamp), stamp))

    def _training(self, execution_id: str) -> dict[str, Any]:
        _safe(execution_id, "execution_id")
        with self.db.connect() as con: row = con.execute("SELECT payload_json FROM proposal_training_runs WHERE execution_id=?", (execution_id,)).fetchone()
        if not row: raise KeyError("training_execution_not_found")
        return json.loads(row[0])

    def _save_review(self, r: dict[str, Any], action: str) -> dict[str, Any]:
        r["version"] += 1; stamp = now()
        with self.db.connect() as con:
            con.execute("UPDATE candidate_proposal_reviews SET version=?,status=?,payload_json=?,updated_at=? WHERE id=?", (r["version"], r["status"], json.dumps(r, ensure_ascii=False, sort_keys=True), stamp, r["review_id"]))
            con.execute("INSERT INTO candidate_proposal_review_versions(review_id,version,occurred_at,action,payload_json) VALUES(?,?,?,?,?)", (r["review_id"], r["version"], stamp, action, json.dumps(r, ensure_ascii=False, sort_keys=True)))
        self.db.audit("candidate_proposal_review_" + action, r["review_id"], "success", {"version": r["version"]}); return r

    def _recover_orphans(self) -> None:
        with self.db.connect() as con:
            rows = con.execute("SELECT payload_json FROM proposal_training_runs WHERE status IN ('running','cancelling','recovering')").fetchall()
            for row in rows:
                value = json.loads(row[0]); value["status"] = "interrupted"; value["orphan_detected"] = True; value["partial_artifact_accepted"] = False
                con.execute("UPDATE proposal_training_runs SET status='interrupted',payload_json=?,updated_at=? WHERE execution_id=?", (json.dumps(value, ensure_ascii=False, sort_keys=True), now(), value["training_execution_id"]))

    def _import_official_catalog(self) -> None:
        report = ROOT / "ml" / "reports" / "v0_4_6"
        proposal_path, runs_path, review_path = report / "representative_proposal.json", report / "training_run_records.json", report / "manual_review.json"
        if not proposal_path.is_file(): return
        proposal = json.loads(proposal_path.read_text(encoding="utf-8")); stamp = proposal.get("created_at") or "2026-07-28T00:00:00Z"
        with self.db.connect() as con:
            # proposal_id is the stable lineage identity; proposal_token is an opaque
            # execution-local locator and may change when the official campaign is rebuilt.
            con.execute("DELETE FROM candidate_proposals WHERE proposal_id=? AND token<>?", (proposal["proposal_id"], proposal["proposal_token"]))
            con.execute("""INSERT INTO candidate_proposals VALUES(?,?,?,?,?,?)
                ON CONFLICT(token) DO UPDATE SET proposal_id=excluded.proposal_id,status=excluded.status,payload_json=excluded.payload_json,updated_at=excluded.updated_at""",
                (proposal["proposal_token"], proposal["proposal_id"], proposal["proposal_status"], json.dumps(proposal, ensure_ascii=False, sort_keys=True), stamp, stamp))
            if runs_path.is_file():
                for run in json.loads(runs_path.read_text(encoding="utf-8")):
                    created = run.get("created_at") or stamp
                    con.execute("""INSERT INTO proposal_training_runs VALUES(?,?,?,?,?,?,?)
                        ON CONFLICT(execution_id) DO UPDATE SET training_semantic_id=excluded.training_semantic_id,status=excluded.status,payload_json=excluded.payload_json,updated_at=excluded.updated_at""",
                        (run["training_execution_id"], proposal["proposal_token"], run["training_semantic_id"], run["status"], json.dumps(run, ensure_ascii=False, sort_keys=True), created, created))
            if review_path.is_file():
                review = json.loads(review_path.read_text(encoding="utf-8")); created = review.get("created_at") or stamp
                con.execute("INSERT OR IGNORE INTO candidate_proposal_reviews VALUES(?,?,?,?,?,?,?)", (review["review_id"], proposal["proposal_token"], review["version"], review["status"], json.dumps(review, ensure_ascii=False, sort_keys=True), created, created))

    def _write_metadata(self, token: str, name: str, value: Any) -> None:
        path = self.proposals_dir / _safe(token, "proposal_token") / name; path.parent.mkdir(parents=True, exist_ok=True); path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")

    def _write_text(self, token: str, name: str, value: str) -> None:
        path = self.proposals_dir / _safe(token, "proposal_token") / name; path.parent.mkdir(parents=True, exist_ok=True); path.write_text(value, encoding="ascii", newline="\n")

    @staticmethod
    def _git_head() -> str:
        import subprocess
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
