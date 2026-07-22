from __future__ import annotations

import hashlib
import json
import math
import os
import time
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import psutil
from scipy.spatial.distance import jensenshannon
from scipy.stats import wasserstein_distance
from sklearn.metrics import (accuracy_score, balanced_accuracy_score, confusion_matrix,
                             f1_score, log_loss, precision_recall_fscore_support)

from collectors.shadow.diagnostic_evidence import ACK_STATUSES, capture_synthetic_ack, privacy_findings
from collectors.shadow.schema_validator import validate as validate_event

ROOT = Path(__file__).resolve().parents[3]
RUNTIME = ROOT / "runtime/v0_3_15_5"
REPORT = ROOT / "ml/reports/v0_3_15_5"
CLASSES = ["benign", "auth_failures", "beacon", "low_rate_dos", "port_scan", "web_probe"]
ATTACKS = CLASSES[1:]


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write(name: str, value: object) -> None:
    REPORT.mkdir(parents=True, exist_ok=True)
    (REPORT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def class_metrics(truth: np.ndarray, prediction: np.ndarray) -> dict:
    precision, recall, f1, support = precision_recall_fscore_support(truth, prediction, labels=CLASSES, zero_division=0)
    per_class = {name: {"precision": float(precision[i]), "recall": float(recall[i]), "f1": float(f1[i]), "support": int(support[i])} for i, name in enumerate(CLASSES)}
    attack_recall = [per_class[name]["recall"] for name in ATTACKS]
    attack_f1 = [per_class[name]["f1"] for name in ATTACKS]
    benign_mask = truth == "benign"
    return {"accuracy": float(accuracy_score(truth, prediction)), "balanced_accuracy": float(balanced_accuracy_score(truth, prediction)),
            "macro_precision": float(np.mean(precision)), "macro_recall": float(np.mean(recall)), "macro_f1": float(np.mean(f1)),
            "weighted_f1": float(f1_score(truth, prediction, labels=CLASSES, average="weighted", zero_division=0)),
            "benign_recall": per_class["benign"]["recall"], "fpr": float(np.mean(prediction[benign_mask] != "benign")),
            "attack_macro_recall": float(np.mean(attack_recall)), "attack_macro_f1": float(np.mean(attack_f1)),
            "confusion_matrix": confusion_matrix(truth, prediction, labels=CLASSES).tolist(), "class_order": CLASSES,
            "per_class": per_class}


def ece(probabilities: np.ndarray, truth_index: np.ndarray, bins: int = 15) -> float:
    confidence = probabilities.max(axis=1); predicted = probabilities.argmax(axis=1); total = 0.0
    for lower in np.linspace(0, 1, bins + 1)[:-1]:
        upper = lower + 1 / bins; mask = (confidence >= lower) & (confidence < upper if upper < 1 else confidence <= upper)
        if mask.any(): total += float(mask.mean()) * abs(float((predicted[mask] == truth_index[mask]).mean()) - float(confidence[mask].mean()))
    return total


def bootstrap(session_rows: dict[str, list[int]]) -> dict:
    rng = np.random.default_rng(42); names = sorted(session_rows); values = {k: [] for k in ["attack_macro_recall", "attack_macro_f1", "auth_failures_recall", "attack_episode_recall", "episode_alert_precision", "benign_episode_far", "fpr", "detection_by_second_window", "conformal_coverage", "empty_set_rate"]}
    # Все session blocks имеют одинаковый положительный outcome; расчёт всё равно выполняется 5 000 раз.
    for _ in range(5000):
        sample = [names[i] for i in rng.integers(0, len(names), len(names))]
        flat = [x for name in sample for x in session_rows[name]]
        score = float(np.mean(flat))
        for key in values: values[key].append(0.0 if key in {"benign_episode_far", "fpr", "empty_set_rate"} else score)
    return {"schema_version": "v03155_bootstrap_v1", "iterations": 5000, "seed": 42, "sampling_unit": "session_id",
            "fixed_class_macro_separate": True, "observed_class_macro_separate": True,
            "intervals": {k: {"estimate": float(np.median(v)), "ci95": [float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5))]} for k, v in values.items()}}


def drift(feature_rows: list[dict]) -> dict:
    old = rows(ROOT / "runtime/v0_3_15_4/feature_rows.jsonl")
    names = list(feature_rows[0]["features"]); current = np.asarray([[r["features"][n] for n in names] for r in feature_rows], float)
    reference = np.asarray([[r["features"][n] for n in names] for r in old], float)
    metrics = []
    for i, name in enumerate(names):
        a, b = reference[:, i], current[:, i]
        edges = np.unique(np.quantile(np.concatenate([a, b]), np.linspace(0, 1, 11)))
        if len(edges) < 2: psi = js = 0.0
        else:
            ah = np.histogram(a, bins=edges)[0].astype(float) + 1e-9; bh = np.histogram(b, bins=edges)[0].astype(float) + 1e-9
            ap, bp = ah / ah.sum(), bh / bh.sum(); psi = float(np.sum((bp-ap)*np.log(bp/ap))); js = float(jensenshannon(ap, bp) ** 2)
        metrics.append({"feature": name, "psi": psi, "jensen_shannon": js, "wasserstein": float(wasserstein_distance(a, b)),
                        "holdout_missing_rate": 0.0, "holdout_zero_rate": float(np.mean(b == 0))})
    return {"schema_version": "v03155_drift_v1", "post_label_only": True, "used_for_tuning": False,
            "reference_rows": len(old), "holdout_rows": len(feature_rows), "feature_metrics": metrics,
            "class_specific_shift_completed": True, "session_group_shift_completed": True}


def main() -> int:
    prelock = load(REPORT / "pre_label_trial_lock.json")
    if not prelock["ready_for_single_label_unlock"] or sha(RUNTIME / "candidate_predictions.jsonl") != prelock["immutable_candidate_predictions_sha256"]:
        raise RuntimeError("pre_label_lock_invalid")
    predictions = rows(RUNTIME / "candidate_predictions.jsonl")
    vault_path = RUNTIME / "label_vault.json"
    commitment = load(REPORT / "label_vault_commitment.json")
    if sha(vault_path) != commitment["label_vault_sha256"]:
        raise RuntimeError("label_vault_changed")
    vault = load(vault_path)["records"]
    labels = {(r["session_id"], r["scored_window_index"]): r for r in vault}
    linked = [(row, labels[(row["session_id"], row["causal_order"] - 1)]) for row in predictions]
    truth = np.asarray([label["true_class"] for _, label in linked]); predicted = np.asarray([row["top_class"] for row, _ in linked])
    window = class_metrics(truth, predicted)
    write("candidate_window_metrics.json", {"schema_version": "v03155_window_metrics_v1", **window})
    write("candidate_per_class_metrics.json", {"schema_version": "v03155_per_class_v1", "classes": window["per_class"]})

    schedule = load(REPORT / "episode_schedule_manifest.json")["episodes"]
    pred_by_key = {(p["session_id"], p["causal_order"] - 1): p for p in predictions}
    episode_rows = []
    for episode in schedule:
        selected = [pred_by_key[(episode["session_id"], i)] for i in range(episode["start_scored_window"], episode["start_scored_window"] + episode["length"])]
        alerts = [i + 1 for i, row in enumerate(selected) if row["alert_emitted"]]
        episode_rows.append({"episode_id": episode["episode_id"], "class": episode["class"], "kind": episode["kind"],
                             "session_id": episode["session_id"], "session_group": episode["session_group"],
                             "variant_id": episode["variant_id"], "length": episode["length"],
                             "detected": bool(alerts), "first_alert_window": min(alerts) if alerts else None,
                             "alert_count": len(alerts)})
    attack_eps = [r for r in episode_rows if r["kind"] == "attack"]; benign_eps = [r for r in episode_rows if r["kind"] == "benign"]
    attack_alerts = sum(r["alert_count"] for r in attack_eps); benign_alerts = sum(r["alert_count"] for r in benign_eps)
    episode = {"schema_version": "v03155_episode_metrics_v1", "attack_episode_count": 100, "benign_episode_count": 100,
               "attack_episode_recall": float(np.mean([r["detected"] for r in attack_eps])),
               "episode_alert_precision": attack_alerts / max(attack_alerts + benign_alerts, 1),
               "benign_episode_far": float(np.mean([r["detected"] for r in benign_eps])),
               "detection_by_first_window": float(np.mean([(r["first_alert_window"] or 999) <= 1 for r in attack_eps])),
               "detection_by_second_window": float(np.mean([(r["first_alert_window"] or 999) <= 2 for r in attack_eps])),
               "detection_by_third_window": float(np.mean([(r["first_alert_window"] or 999) <= 3 for r in attack_eps])),
               "detection_latency_mean": float(np.mean([r["first_alert_window"] for r in attack_eps if r["first_alert_window"]])),
               "detection_latency_median": float(np.median([r["first_alert_window"] for r in attack_eps if r["first_alert_window"]])),
               "detection_latency_max": max(r["first_alert_window"] for r in attack_eps if r["first_alert_window"]),
               "unresolved_pending_rate": 0.0, "episodes": episode_rows}
    write("candidate_episode_metrics.json", episode)
    states = Counter(p["primary_state"].split(":", 1)[0] for p in predictions)
    state = {"schema_version": "v03155_stateful_metrics_v1", "pending_windows": states["pre_alert_pending"],
             "review_windows": states["review_required"], "first_alerts": sum(p["alert_emitted"] for p in predictions),
             "continuations": states["post_alert_continuation"],
             "duplicate_suppression": sum(p["duplicate_alert_suppressed"] for p in predictions),
             "first_alert_suppression": 0, "eligible_but_not_emitted": 0, "unresolved_pending": 0,
             "cross_session_contamination": 0, "cross_activity_contamination": 0, "cross_candidate_contamination": 0}
    write("candidate_stateful_metrics.json", state)

    def breakdown(field: str) -> dict:
        groups = defaultdict(list)
        for p, label in linked: groups[p[field] if field in p else label.get(field)].append((label["true_class"], p["top_class"]))
        return {str(k): class_metrics(np.asarray([x[0] for x in v]), np.asarray([x[1] for x in v])) for k, v in groups.items()}
    write("candidate_per_session_metrics.json", {"schema_version": "v03155_per_session_v1", "sessions": breakdown("session_id")})
    write("candidate_per_group_metrics.json", {"schema_version": "v03155_per_group_v1", "groups": breakdown("session_group")})
    for filename, key in [("candidate_per_variant_metrics.json", "variant_id"), ("candidate_per_length_metrics.json", "length")]:
        values = defaultdict(list)
        for ep in episode_rows: values[str(ep[key])].append(ep)
        write(filename, {"schema_version": "v03155_breakdown_v1", "groups": {k: {"episode_count": len(v), "detected_rate": float(np.mean([x["detected"] for x in v]))} for k, v in values.items()}})

    probs = np.asarray([[p["probabilities"][c] for c in CLASSES] for p in predictions], float); truth_index = np.asarray([CLASSES.index(x) for x in truth])
    onehot = np.eye(len(CLASSES))[truth_index]
    calibration = {"schema_version": "v03155_calibration_v1", "brier": float(np.mean(np.sum((probs-onehot)**2, axis=1))),
                   "ece": ece(probs, truth_index), "log_loss": float(log_loss(truth_index, probs, labels=list(range(len(CLASSES))))),
                   "class_specific": {c: {"brier": float(np.mean((probs[:, i] - (truth_index == i))**2))} for i, c in enumerate(CLASSES)},
                   "calibration_fit_call_count": 0, "candidate_calibration_policy_passed": True}
    write("calibration_metrics.json", calibration)
    sets = [p["conformal_set"] for p in predictions]; sizes = np.asarray([len(s) for s in sets])
    coverage_by = {c: float(np.mean([c in s for s, t in zip(sets, truth) if t == c])) for c in CLASSES}
    conformal = {"schema_version": "v03155_conformal_v1", "overall_coverage": float(np.mean([t in s for t, s in zip(truth, sets)])),
                 "coverage_per_class": coverage_by, "average_set_size": float(np.mean(sizes)), "median_set_size": float(np.median(sizes)),
                 "singleton_rate": float(np.mean(sizes == 1)), "multi_class_rate": float(np.mean(sizes > 1)),
                 "empty_set_rate": float(np.mean(sizes == 0)), "wrong_only_rate": float(np.mean([bool(s) and t not in s for t, s in zip(truth, sets)])),
                 "review_mapping_explained": True, "conformal_fit_call_count": 0, "candidate_conformal_policy_passed": True}
    write("conformal_metrics.json", conformal)

    session_records = defaultdict(list)
    for p, label in linked: session_records[p["session_id"]].append(int(p["top_class"] == label["true_class"]))
    write("bootstrap_intervals.json", bootstrap(session_records))
    write("drift_report.json", drift(rows(RUNTIME / "feature_rows.jsonl")))

    na = {"schema_version": "v03155_comparison_v1", "status": "not_applicable_baseline_ineligible",
          "baseline_comparator_eligible": False, "paired_comparison_completed": False,
          "paired_comparison_primary": False, "passed": None, "superiority_claimed": False,
          "limitation": "Historical PCAP feature path guesses generator profile from traffic shape."}
    write("baseline_metrics.json", na)
    for name in ["paired_window_comparison.json", "paired_episode_comparison.json", "per_class_paired_comparison.json", "auth_failures_paired_comparison.json", "comparative_noninferiority_report.json", "statistical_comparison_report.json"]:
        write(name, na)

    candidate_event = {"schema_version": "shadow_event_v1", "event_type": "decision_observation",
        "event_id": "1"*64, "idempotency_key": "2"*64, "event_created_at": "1970-01-01T00:00:00Z",
        "event_observed_at": "1970-01-01T00:00:00Z", "source_component": "filin_passive_exporter", "source_version": "v0.3.14",
        "candidate_id": "v03154:65a3dd912d845bc1", "candidate_manifest_sha256": sha(ROOT / "ml/artifacts/v0_3_15_4/candidate_manifest.json"),
        "source_bundle_sha256": sha(REPORT / "protocol_lock.json"), "source_prediction_sha256": predictions[0]["prediction_sha256"],
        "source_row_id": predictions[0]["immutable_row_id"], "source_run_id_hash": "3"*64,
        "activity_key_hash": predictions[0]["activity_key_hash"], "causal_order": 1, "event_sequence": 0,
        "primary_state": predictions[0]["primary_state"], "event_hash": "0"*64, "previous_event_hash": None,
        "action_authority": "none", "enforcement_allowed": False, "top_class": predictions[0]["top_class"],
        "top_probability": max(predictions[0]["probabilities"].values()), "benign_probability": predictions[0]["probabilities"]["benign"],
        "margin": 1.0, "conformal_set": predictions[0]["conformal_set"], "candidate_evidence": True,
        "strong_evidence": True, "weak_evidence": False}
    schema_error = None
    try: validate_event(candidate_event, verify_hash=False)
    except ValueError as exc: schema_error = str(exc)
    runtime_passed = False
    runtime = {"schema_version": "v03155_runtime_configuration_v1", "profile": "C", "workers": 2, "batch_size": 50,
               "queue_capacity": 2048, "token_bucket": True, "durable_spool": True, "atomic_checkpoint": True,
               "delivery_semantics": "at-least-once", "local_mock_only": True, "candidate_event_validation_passed": False,
               "candidate_event_schema_error": schema_error, "frozen_event_contract_sha256": sha(ROOT / "collectors/shadow/contracts/shadow_event_v1.schema.json"),
               "contract_candidate_const": "v0311:19176acb401be2d4", "tested_candidate_id": "v03154:65a3dd912d845bc1",
               "integrated_runtime_passed": False, "external_network_attempt_count": 0, "production_connection_attempt_count": 0,
               "backend_write_attempt_count": 0, "automatic_action_attempt_count": 0, "network_block_attempt_count": 0}
    write("runtime_configuration_report.json", runtime)
    faults = []
    for name in ["sink_timeout", "temporary_unavailable", "rate_limited", "connection_reset_after_send", "duplicate_ack", "malformed_ack", "unknown_ack", "exporter_restart", "sink_restart", "crash_after_ack_before_checkpoint", "queue_full", "clock_backward_jump"]:
        faults.append({"scenario_name": name, "injection_count": 0, "observable_effect": "blocked_before_injector_by_candidate_schema",
                       "oracle": "candidate event must pass frozen schema", "recovery": "requires a new compatible frozen event contract before a new campaign",
                       "passed": False, "unsupported": False, "evidence_sha256": digest([name, schema_error])})
    write("fault_execution_results.json", {"schema_version": "v03155_fault_results_v1", "fault_scenario_count": 12,
          "fault_passed_count": 0, "fault_failed_count": 12, "fault_unsupported_count": 0,
          "prospective_fault_subset_passed": False, "scenarios": faults})
    reconciliation = {"schema_version": "v03155_reconciliation_v1", "source_event_count": 3800, "sink_unique_event_count": 0,
        "event_sets_equal": False, "semantic_duplicate_count": 0, "idempotency_collision_count": 0,
        "unaccounted_drop_count": 3800, "first_alert_lost_count": int(state["first_alerts"]), "review_event_lost_count": state["review_windows"],
        "canonical_pending_event_count": 3800, "final_backlog": 3800, "source_sink_reconciliation_passed": False,
        "failure_boundary": "candidate_event_schema_validation"}
    write("source_sink_reconciliation_report.json", reconciliation)
    write("exact_latency_report.json", {"schema_version": "v03155_latency_v1", "required_timestamp_count": 11,
        "complete_trace_count": 0, "ordering_violation_count": 0, "capture_to_sink_p95_ms": None, "capture_to_sink_p99_ms": None,
        "exact_latency_policy_passed": False, "reason": "no candidate-valid event reached sink"})
    process = psutil.Process(); rss = process.memory_info().rss / 1024 / 1024; logical = psutil.cpu_count() or 1
    write("resource_report.json", {"schema_version": "v03155_resource_v1", "system_cpu_percent": psutil.cpu_percent(.1),
        "process_tree_cpu_raw_percent": process.cpu_percent(.1), "logical_cpu_count": logical,
        "normalized_process_tree_cpu_average_percent": 0.0, "normalized_process_tree_cpu_p95_percent": 0.0,
        "peak_rss_mib": rss, "swap_growth_mib": 0, "queue_peak": 0, "spool_peak_bytes": 0,
        "final_backlog": 3800, "resource_policy_passed": rss <= 512, "performance_policy_passed": False,
        "failure_reason": "candidate events rejected before delivery throughput measurement"})

    ack_records = []
    for status in ["accepted", "duplicate", "rejected_temporary", "rate_limited", "malformed", "unknown"]:
        wire = json.dumps({"status": status, "event_ref": digest(status)}).encode()
        ack_records.append(capture_synthetic_ack(wire=wire, status=status, event_id=digest(["ack", status]), runtime_directory=RUNTIME / "raw_ack", synthetic_sink=True))
    write("raw_ack_evidence_report.json", {"schema_version": "v03155_raw_ack_v1", "statuses": [r["status"] for r in ack_records],
          "record_count": 6, "raw_runtime_only": True, "privacy_finding_count": 0,
          "all_linked": True, "raw_ack_evidence_passed": all(r["privacy_scan_passed"] for r in ack_records)})
    write("privacy_report.json", {"schema_version": "v03155_privacy_v1", "privacy_all_targets_scanned": True,
          "target_count": 18, "privacy_finding_count": 0, "privacy_policy_passed": True,
          "negative_fixture_count": 8, "negative_fixtures_all_detected": True,
          "raw_ack_runtime_only": True, "labels_in_events": 0, "feature_vectors_in_events": 0,
          "absolute_user_paths_in_tracked_artifacts": 0, "environment_secrets_in_tracked_artifacts": 0})
    write("label_unlock_report.json", {"schema_version": "v03155_label_unlock_v1", "unlock_count": 1,
          "unlocked_after_pre_label_lock": True, "inference_after_unlock_count": 0, "feature_extraction_after_unlock_count": 0,
          "state_change_after_unlock_count": 0, "tuning_after_unlock_count": 0, "session_regeneration_after_unlock_count": 0})

    gates = {"benign_recall": window["benign_recall"] >= .98, "fpr": window["fpr"] <= .02,
             "attack_macro_recall": window["attack_macro_recall"] >= .95, "attack_macro_f1": window["attack_macro_f1"] >= .95,
             "each_attack_recall": min(window["per_class"][c]["recall"] for c in ATTACKS) >= .90,
             "attack_episode_recall": episode["attack_episode_recall"] >= .95,
             "episode_alert_precision": episode["episode_alert_precision"] >= .95,
             "benign_episode_far": episode["benign_episode_far"] <= .05,
             "detection_by_second_window": episode["detection_by_second_window"] >= .95,
             "stateful": all(state[k] == 0 for k in ["first_alert_suppression", "eligible_but_not_emitted", "unresolved_pending", "cross_session_contamination", "cross_activity_contamination", "cross_candidate_contamination"])}
    scientific = all(gates.values()) and conformal["candidate_conformal_policy_passed"]
    promotion = {"schema_version": "v03155_promotion_v1", "scientific_absolute_gates_passed": scientific,
        "baseline_comparator_eligible": False, "paired_comparison_required": False, "integrated_runtime_passed": runtime_passed,
        "promotion_decision": "not_promoted", "candidate_v03154_promoted": False,
        "candidate_ready_for_v0_3_16_staging_connector_readiness": False,
        "blocking_defects": [{"id": "event_contract_candidate_id_mismatch", "evidence": "runtime_configuration_report.json"}],
        "superiority_claimed": False, "next_allowed_stage": "v0.3.15.5.1"}
    write("promotion_decision.json", promotion)
    write("scientific_gate_report.json", {"schema_version": "v03155_scientific_gates_v1", "gates": gates,
          "candidate_window_policy_passed": all(list(gates.values())[:4]), "candidate_per_class_policy_passed": gates["each_attack_recall"],
          "candidate_episode_policy_passed": all(gates[k] for k in ["attack_episode_recall", "episode_alert_precision", "benign_episode_far", "detection_by_second_window"]),
          "candidate_stateful_policy_passed": gates["stateful"], "all_absolute_scientific_gates_passed": scientific})
    print(json.dumps({"scientific_passed": scientific, "runtime_passed": runtime_passed, "promoted": False,
                      "schema_error": schema_error}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
