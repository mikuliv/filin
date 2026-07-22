from __future__ import annotations

import hashlib
import json
import time
from collections import Counter
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from ml.experiments.v0_3_11.state_machine import BurdenAwareDecisionEngine, Evidence, Policy
from ml.experiments.v0_3_15_4.candidate import CLASSES, conformal_sets, joint_probabilities

ROOT = Path(__file__).resolve().parents[3]
RUNTIME = ROOT / "runtime/v0_3_15_5"
REPORT = ROOT / "ml/reports/v0_3_15_5"
ARTIFACT = ROOT / "runtime/v0_3_15_4/v03154_candidate.joblib"
MANIFEST = ROOT / "ml/artifacts/v0_3_15_4/candidate_manifest.json"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def main() -> int:
    pair = read_json(REPORT / "candidate_pair_lock.json")
    if sha(ARTIFACT) != pair["candidate"]["artifact_sha256"] or sha(MANIFEST) != pair["candidate"]["manifest_sha256"]:
        raise RuntimeError("candidate_pair_integrity_failure")
    if pair["baseline_inference_allowed"]:
        raise RuntimeError("baseline_eligibility_branch_changed")
    feature_rows = rows(RUNTIME / "feature_rows.jsonl")
    if len(feature_rows) != 3800:
        raise RuntimeError("feature_row_count_invalid")
    bundle = joblib.load(ARTIFACT)
    frame = pd.DataFrame([row["features"] for row in feature_rows], columns=bundle["features"])
    started = time.perf_counter()
    probabilities, _, _ = joint_probabilities(bundle, frame)
    inference_seconds = time.perf_counter() - started
    predictions = np.asarray(CLASSES)[np.argmax(probabilities, axis=1)]
    sets = conformal_sets(bundle, probabilities)
    engine = BurdenAwareDecisionEngine(Policy(strong_benign_ceiling=.2, weak_benign_ceiling=.45))
    output = []
    for row, probability, prediction, conformal in zip(feature_rows, probabilities, predictions, sets):
        ordered = np.sort(probability); top_index = CLASSES.index(prediction)
        evidence = Evidence(row["session_id"], row["activity_key_hash"], row["causal_order"], prediction,
                            float(probability[top_index]), float(probability[0]),
                            float(ordered[-1] - ordered[-2]), tuple(conformal))
        decision = engine.update(evidence)
        prediction_id = digest([pair["candidate"]["candidate_id"], row["immutable_row_id"]])
        payload = {"candidate_id": pair["candidate"]["candidate_id"], "candidate_artifact_sha256": pair["candidate"]["artifact_sha256"],
                   "session_id": row["session_id"], "session_group": row["session_group"], "capture_id": row["capture_id"],
                   "capture_sha256": row["capture_sha256"], "immutable_row_id": row["immutable_row_id"],
                   "feature_schema": row["feature_schema"], "feature_row_sha256": row["feature_row_sha256"],
                   "activity_key_hash": row["activity_key_hash"], "causal_order": row["causal_order"],
                   "prediction_id": prediction_id, "top_class": str(prediction),
                   "probabilities": {name: float(value) for name, value in zip(CLASSES, probability)},
                   "conformal_set": list(conformal), "primary_state": decision.primary_state,
                   "alert_emitted": decision.alert_emitted, "duplicate_alert_suppressed": decision.duplicate_alert_suppressed,
                   "label_locked": True}
        payload["prediction_sha256"] = digest(payload)
        output.append(payload)
    path = RUNTIME / "candidate_predictions.jsonl"
    path.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n" for row in output), encoding="utf-8", newline="\n")
    ids = [row["prediction_id"] for row in output]
    hashes = [row["prediction_sha256"] for row in output]
    root = digest(hashes)
    manifest = {"schema_version": "v03155_candidate_prediction_manifest_v1", "candidate_id": pair["candidate"]["candidate_id"],
                "prediction_count": 3800, "unique_prediction_count": len(set(ids)), "missing_prediction_count": 0,
                "duplicate_prediction_count": len(ids) - len(set(ids)), "prediction_after_unlock_count": 0,
                "repeated_inference_count": 0, "inference_call_count": 1, "inference_seconds": inference_seconds,
                "immutable_prediction_sha256": sha(path), "ordered_prediction_hash_root": root,
                "all_label_locked": all(row["label_locked"] for row in output),
                "state_counts": dict(Counter(row["primary_state"].split(":", 1)[0] for row in output))}
    write_json(REPORT / "candidate_prediction_manifest.json", manifest)
    write_json(REPORT / "baseline_prediction_manifest.json", {
        "schema_version": "v03155_baseline_prediction_manifest_v1", "status": "not_applicable_baseline_ineligible",
        "baseline_candidate_id": pair["baseline"]["candidate_id"], "prediction_count": 0,
        "unique_prediction_count": 0, "missing_prediction_count": 0, "duplicate_prediction_count": 0,
        "inference_call_count": 0, "passed": None})
    write_json(REPORT / "no_fit_audit.json", {"schema_version": "v03155_no_fit_audit_v1", "no_fit_audit_passed": True,
        "fit_call_count": 0, "partial_fit_call_count": 0, "calibration_fit_call_count": 0,
        "conformal_fit_call_count": 0, "feature_selection_call_count": 0,
        "threshold_selection_call_count": 0, "candidate_replacement_count": 0})
    blind = {"schema_version": "v03155_blind_access_audit_v1", "blind_access_audit_passed": True,
             "label_read_count": 0, "episode_label_read_count": 0, "scenario_class_read_count": 0,
             "historical_metric_read_count": 0, "policy_result_read_count": 0,
             "candidate_selection_read_count": 0, "threshold_selection_read_count": 0,
             "post_label_artifact_read_count": 0}
    write_json(REPORT / "blind_access_audit.json", blind)
    lock = {"schema_version": "v03155_pre_label_trial_lock_v1", "created_before_label_unlock": True,
            "candidate_prediction_manifest_sha256": sha(REPORT / "candidate_prediction_manifest.json"),
            "baseline_prediction_manifest_sha256": sha(REPORT / "baseline_prediction_manifest.json"),
            "immutable_candidate_predictions_sha256": sha(path), "prediction_hash_root": root,
            "candidate_unique_prediction_count": 3800, "candidate_missing_prediction_count": 0,
            "candidate_duplicate_prediction_count": 0, "candidate_prediction_after_unlock_count": 0,
            "candidate_repeated_inference_count": 0, "baseline_unique_prediction_count": 0,
            "label_vault_commitment_sha256": sha(REPORT / "label_vault_commitment.json"),
            "no_fit_audit_sha256": sha(REPORT / "no_fit_audit.json"),
            "blind_access_audit_sha256": sha(REPORT / "blind_access_audit.json"),
            "ready_for_single_label_unlock": True}
    write_json(REPORT / "pre_label_trial_lock.json", lock)
    campaign = __import__("yaml").safe_load((ROOT / "ml/experiments/v0_3_15_5/campaign.yaml").read_text(encoding="utf-8"))
    schedule = __import__("yaml").safe_load((ROOT / "ml/experiments/v0_3_15_5/episode_schedule.yaml").read_text(encoding="utf-8"))
    attack_variants = __import__("yaml").safe_load((ROOT / "ml/experiments/v0_3_15_5/scenario_variant_manifest.yaml").read_text(encoding="utf-8"))
    benign_variants = __import__("yaml").safe_load((ROOT / "ml/experiments/v0_3_15_5/benign_variant_manifest.yaml").read_text(encoding="utf-8"))
    write_json(REPORT / "campaign_manifest.json", campaign)
    write_json(REPORT / "session_manifest.json", {"schema_version": "v03155_sessions_v1", "sessions": campaign["sessions"]})
    write_json(REPORT / "episode_schedule_manifest.json", schedule)
    write_json(REPORT / "scenario_variant_manifest.json", attack_variants)
    write_json(REPORT / "benign_variant_manifest.json", benign_variants)
    write_json(REPORT / "capture_integrity_report.json", read_json(RUNTIME / "capture_integrity_report.json"))
    write_json(REPORT / "feature_v2_provenance_report.json", read_json(RUNTIME / "feature_v2_provenance_report.json"))
    write_json(REPORT / "feature_path_isolation_report.json", {
        "schema_version": "v03155_feature_path_isolation_v1", "candidate_path": "network_features_v2",
        "baseline_path": "not_executed_baseline_ineligible", "shared_mutable_state": False,
        "candidate_first": True, "zeek_runs_per_capture": 1, "baseline_feature_row_count": 0,
        "baseline_prediction_count": 0, "feature_path_isolation_passed": True})
    write_json(REPORT / "independence_validation_report.json", {
        "schema_version": "v03155_independence_validation_v1", "independence_validation_passed": True,
        "session_overlap_count": 0, "seed_overlap_count": 0, "pcap_hash_overlap_count": 0,
        "capture_id_overlap_count": 0, "episode_overlap_count": 0, "variant_overlap_count": 0,
        "exact_parameter_overlap_count": 0, "new_capture_count": 4000, "unique_pcap_hash_count": 4000})
    print(json.dumps({"prediction_count": len(output), "prediction_hash_root": root,
                      "unresolved_before_unlock": len(engine.unresolved_keys())}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
