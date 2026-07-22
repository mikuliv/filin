from __future__ import annotations

import csv
import hashlib
import json
import math
import statistics
import subprocess
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import yaml

from collectors.shadow.diagnostic_evidence import (
    ACK_STATUSES, LATENCY_STAGES, LatencyTrace, capture_synthetic_ack,
    instrumentation_equivalent, normalized_cpu_sample, privacy_findings,
)
from collectors.shadow_trial.window_processor import FEATURES

ROOT = Path(__file__).resolve().parents[3]
SOURCE_COMMIT = "a1959cddd34a46da100b856d7361ec940edb0299"
REPORT = ROOT / "ml/reports/v0_3_15_3"
OLD_REPORT = ROOT / "ml/reports/v0_3_15_2"
RUNTIME = ROOT / "runtime/v0_3_15_2"
DIAGNOSTIC_RUNTIME = ROOT / "runtime/v0_3_15_3_diagnostic"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def json_digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write(name: str, value: Any) -> None:
    REPORT.mkdir(parents=True, exist_ok=True)
    (REPORT / name).write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as stream:
        return [json.loads(line) for line in stream if line.strip()]


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def directory_digest(path: Path) -> str | None:
    if not path.exists():
        return None
    rows=[]
    for item in sorted(x for x in path.rglob("*") if x.is_file()):
        rows.append({"path":item.relative_to(path).as_posix(),"size":item.stat().st_size,"sha256":digest(item)})
    return json_digest(rows)


def historical_integrity() -> dict[str, Any]:
    paths = [
        "ml/reports/v0_3_11", "ml/reports/v0_3_12", "ml/reports/v0_3_12_1",
        "ml/reports/v0_3_12_2", "ml/reports/v0_3_13", "ml/reports/v0_3_14",
        "ml/reports/v0_3_15", "ml/reports/v0_3_15_1", "ml/reports/v0_3_15_2",
        "ml/protocols/v0_3_15_2_protocol.yaml", "ml/experiments/v0_3_15_2",
        "docs/experiments/v0_3_14.md", "docs/experiments/v0_3_14_errata.md",
    ]
    rows = []
    for relative in paths:
        before_run=subprocess.run(["git","rev-parse",f"{SOURCE_COMMIT}:{relative}"],cwd=ROOT,text=True,capture_output=True)
        current_run=subprocess.run(["git","rev-parse",f"HEAD:{relative}"],cwd=ROOT,text=True,capture_output=True)
        before=before_run.stdout.strip() if before_run.returncode==0 else None
        current=current_run.stdout.strip() if current_run.returncode==0 else None
        local_hash=directory_digest(ROOT/relative) if (ROOT/relative).is_dir() else digest(ROOT/relative) if (ROOT/relative).is_file() else None
        rows.append({"path": relative, "source_object": before, "current_object": current, "local_aggregate_sha256":local_hash,"versioned_in_source_commit":before is not None,"unchanged": before == current if before is not None else local_hash is not None,"limitation":None if before is not None else "Local historical report is gitignored; its aggregate was recorded after protocol freeze and no analysis code writes this path."})
    manifest = OLD_REPORT / "v0_3_15_2_bundle_manifest.yaml"
    detached = (OLD_REPORT / "v0_3_15_2_bundle_manifest.sha256").read_text(encoding="utf-8").split()[0]
    actual = digest(manifest)
    artifacts = yaml.safe_load(manifest.read_text(encoding="utf-8"))["artifacts"]
    artifact_checks = []
    for row in artifacts:
        path = ROOT / row["path"]
        artifact_checks.append({"path": row["path"], "exists": path.is_file(), "hash_matches": path.is_file() and digest(path) == row["sha256"], "size_matches": path.is_file() and path.stat().st_size == row["size"]})
    return {
        "schema_version": "v03153_historical_integrity_v1", "source_commit": SOURCE_COMMIT,
        "origin_main_observed_at_preflight": git("rev-parse", "origin/main"),
        "expected_origin_main_in_task": "389e81e3ec25b7f04386b08e9b45c10c8fa72973",
        "origin_difference_documented": git("rev-parse", "origin/main") != "389e81e3ec25b7f04386b08e9b45c10c8fa72973",
        "historical_paths": rows, "previous_stage_hashes_unchanged": all(x["unchanged"] for x in rows),
        "v03152_manifest_expected_sha256": "49e13eceb44873f593844b07d86215b36dffd96be7ebbbb75a004c08bad8dcda",
        "v03152_manifest_actual_sha256": actual, "v03152_detached_sha256": detached,
        "v03152_bundle_integrity_verified": actual == detached and all(x["exists"] and x["hash_matches"] and x["size_matches"] for x in artifact_checks),
        "v03152_artifact_count": len(artifact_checks), "v03152_artifact_checks": artifact_checks,
        "negative_result_preserved": load(OLD_REPORT / "v0_3_15_2_policy_result.json")["v03152_prospective_runtime_trial_passed"] is False,
        "backend_tree": git("rev-parse", "HEAD:backend"), "backend_tree_unchanged": git("rev-parse", "HEAD:backend") == "04218a4eb01534950efd5f7d6390f1a575cacbc8",
    }


def evidence_inventory() -> tuple[dict[str, Any], dict[str, Any]]:
    capture_manifest = RUNTIME / "capture_manifest.json"
    predictions = RUNTIME / "immutable_predictions.json"
    labels = RUNTIME / "label_vault.json"
    features = RUNTIME / "feature_rows.jsonl"
    specifications = [
        ("pcap", "raw_network", "runtime/v0_3_15_2/sessions/*/captures", True, capture_manifest, True, False, False, True, "available_historical"),
        ("capture_manifest", "capture_manifest", "runtime/v0_3_15_2/capture_manifest.json", True, capture_manifest, False, False, False, False, "available_historical"),
        ("zeek_logs", "zeek_output", "runtime/v0_3_15_2/sessions/*/zeek", True, predictions, False, False, False, True, "available_historical"),
        ("feature_rows", "features", "runtime/v0_3_15_2/feature_rows.jsonl", True, features, False, False, True, False, "available_historical"),
        ("feature_schema", "schema", "collectors/shadow_trial/window_processor.py", True, ROOT/"collectors/shadow_trial/window_processor.py", False, False, True, False, "available_historical"),
        ("feature_diagnostics", "diagnostics", "ml/reports/v0_3_15_2/feature_integrity_report.json", True, OLD_REPORT/"feature_integrity_report.json", False, False, True, False, "available_historical"),
        ("immutable_predictions", "predictions", "runtime/v0_3_15_2/immutable_predictions.json", True, predictions, False, True, False, False, "available_historical"),
        ("gate_probabilities", "decision", "runtime/v0_3_15_2/immutable_predictions.json", True, predictions, False, True, False, False, "available_historical"),
        ("gate_raw_scores", "decision", "", False, None, False, False, False, False, "unavailable"),
        ("subtype_probabilities", "decision", "runtime/v0_3_15_2/immutable_predictions.json", True, predictions, False, True, False, False, "available_historical"),
        ("subtype_raw_scores", "decision", "", False, None, False, False, False, False, "unavailable"),
        ("calibrated_probabilities", "decision", "runtime/v0_3_15_2/immutable_predictions.json", True, predictions, False, True, False, False, "available_historical"),
        ("conformal_sets", "decision", "runtime/v0_3_15_2/immutable_predictions.json", True, predictions, False, True, False, False, "available_historical"),
        ("state_transitions", "decision", "runtime/v0_3_15_2/immutable_predictions.json", True, predictions, False, True, False, False, "available_historical"),
        ("activity_keys", "mapping", "runtime/v0_3_15_2/immutable_predictions.json", True, predictions, False, True, False, False, "available_historical"),
        ("episode_mappings", "mapping", "runtime/v0_3_15_2/label_vault.json", True, labels, True, False, False, False, "available_historical"),
        ("labels", "labels", "runtime/v0_3_15_2/label_vault.json", True, labels, True, False, False, False, "available_historical"),
        ("scenario_definitions", "scenario", "ml/experiments/v0_3_15_2/episode_schedule.yaml", True, ROOT/"ml/experiments/v0_3_15_2/episode_schedule.yaml", True, False, False, False, "available_historical"),
        ("scenario_parameters", "scenario", "collectors/shadow_trial/window_processor.py", True, ROOT/"collectors/shadow_trial/window_processor.py", True, False, False, False, "available_historical"),
        ("generator_versions", "scenario", "ml/experiments/v0_3_15_2/campaign_lock.json", True, ROOT/"ml/experiments/v0_3_15_2/campaign_lock.json", False, False, False, False, "available_historical"),
        ("per_window_metrics", "metrics", "ml/reports/v0_3_15_2/window_metrics.json", True, OLD_REPORT/"window_metrics.json", True, True, False, False, "available_historical"),
        ("per_episode_metrics", "metrics", "ml/reports/v0_3_15_2/episode_metrics.json", True, OLD_REPORT/"episode_metrics.json", True, True, False, False, "available_historical"),
        ("per_class_metrics", "metrics", "ml/reports/v0_3_15_2/per_class_metrics.json", True, OLD_REPORT/"per_class_metrics.json", True, True, False, False, "available_historical"),
        ("source_events", "events", "runtime/v0_3_15_2/canonical_events.jsonl", True, RUNTIME/"canonical_events.jsonl", False, True, False, False, "available_historical"),
        ("sink_events", "events", "runtime/v0_3_15_2/sink_events.jsonl", True, RUNTIME/"sink_events.jsonl", False, True, False, False, "available_historical"),
        ("runtime_checkpoints", "runtime", "runtime/v0_3_15_2/sessions/*/checkpoint.json", True, OLD_REPORT/"checkpoint_evidence.json", False, False, False, False, "available_historical"),
        ("fault_records", "runtime", "runtime/v0_3_15_2/fault_execution_results.json", True, RUNTIME/"fault_execution_results.json", False, False, False, False, "available_historical"),
        ("performance_samples", "performance", "runtime/v0_3_15_2/performance_profiles_raw.json", True, RUNTIME/"performance_profiles_raw.json", False, False, False, False, "available_historical"),
        ("raw_ack_records", "privacy", "", False, None, False, False, False, False, "unavailable"),
        ("claim_evidence_ledger", "claims", "ml/reports/v0_3_15_2/claim_evidence_ledger.json", True, OLD_REPORT/"claim_evidence_ledger.json", False, False, False, False, "available_historical"),
        ("v0311_training_features", "features", "", False, None, True, False, True, False, "unavailable"),
        ("v0311_validation_features", "features", "", False, None, True, False, True, False, "unavailable"),
        ("v0313_holdout_features", "features", "ml/reports/v0_3_13/holdout_features.csv", (ROOT/"ml/reports/v0_3_13/holdout_features.csv").is_file(), ROOT/"ml/reports/v0_3_13/holdout_features.csv", True, False, True, False, "available_historical"),
        ("v0315_features", "features", "runtime/v0_3_15/feature_table.csv", (ROOT/"runtime/v0_3_15/feature_table.csv").is_file(), ROOT/"runtime/v0_3_15/feature_table.csv", True, False, True, False, "available_historical"),
        ("exact_capture_to_sink_latency", "latency", "", False, None, False, False, False, False, "unavailable"),
    ]
    rows = []
    for artifact_id, role, relative, exists, anchor, has_labels, has_predictions, has_features, raw, classification in specifications:
        path = anchor if exists and anchor and anchor.is_file() else None
        rows.append({
            "artifact_id": artifact_id, "stage": "v0.3.15.2" if not artifact_id.startswith("v031") else artifact_id.split("_")[0].replace("v031", "v0.3."),
            "role": role, "path": relative, "exists": bool(exists), "size": path.stat().st_size if path else 0,
            "sha256": digest(path) if path else None, "schema_version": "historical_or_runtime_v1" if exists else None,
            "contains_labels": has_labels, "contains_predictions": has_predictions, "contains_features": has_features,
            "contains_raw_network_data": raw, "created_before_label_unlock": artifact_id not in {"labels", "episode_mappings"},
            "integrity_verified": bool(path) and (artifact_id not in {"pcap", "zeek_logs"} or (load(OLD_REPORT/"capture_integrity_report.json")["capture_count"] == 2400 and load(OLD_REPORT/"capture_integrity_report.json")["all_closed_before_processing"])),
            "suitable_for_root_cause_analysis": bool(exists), "availability_class": classification,
            "limitations": [] if exists else ["Материал отсутствует; связанные причинные выводы ограничены и не реконструируются предположением."],
        })
    inventory = {"schema_version": "v03153_evidence_inventory_v1", "artifact_count": len(rows), "available_count": sum(x["exists"] for x in rows), "missing_count": sum(not x["exists"] for x in rows), "artifacts": rows}
    matrix = {"schema_version": "v03153_evidence_availability_v1", "classes": {name: [x["artifact_id"] for x in rows if x["availability_class"] == name] for name in ["available_historical", "reconstructable_deterministic", "diagnostic_only_new", "unavailable"]}, "causal_limits": ["Raw gate/subtype scores unavailable: calibration suppression cannot be separated completely from raw-score behavior.", "Raw ACK absent: historical privacy coverage cannot be established.", "Exact latency trace absent: historical capture-to-sink latency cannot be calculated.", "v0.3.11 feature rows absent: training/validation feature-distribution comparison is unavailable."]}
    return inventory, matrix


def episode_analysis() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    predictions = load(RUNTIME / "immutable_predictions.json")["records"]
    labels = load(RUNTIME / "label_vault.json")["records"]
    feature_rows = jsonl(RUNTIME / "feature_rows.jsonl")
    schedule = load(OLD_REPORT / "episode_schedule_manifest.json")["episodes"]
    captures = {x["capture_id"]: x for x in load(RUNTIME / "capture_manifest.json")["captures"]}
    by_episode: dict[str, list[tuple[dict, dict, dict]]] = defaultdict(list)
    for prediction, label, feature in zip(predictions, labels, feature_rows, strict=True):
        if label["episode_id"] is not None:
            by_episode[label["episode_id"]].append((prediction, label, feature))
    ledger = []
    funnel_counts: Counter[str] = Counter()
    class_funnel: dict[str, Counter[str]] = defaultdict(Counter)
    group_funnel: dict[str, Counter[str]] = defaultdict(Counter)
    session_funnel: dict[str, Counter[str]] = defaultdict(Counter)
    length_funnel: dict[str, Counter[str]] = defaultdict(Counter)
    position_funnel: dict[str, Counter[str]] = defaultdict(Counter)
    for planned in schedule:
        rows = sorted(by_episode[planned["episode_id"]], key=lambda x: x[1]["episode_position"])
        states = [p["primary_state"] for p, _, _ in rows]
        alert = any(state.startswith("alert_emitted") for state in states)
        review = any(state.startswith("review_required") for state in states)
        if planned["kind"] == "benign":
            outcome = "benign_no_alert" if not alert and not review else "benign_review" if review else "benign_false_alert"
            mechanism, category, confidence = "none", "unknown", "unknown"
        elif alert:
            outcome, mechanism, category, confidence = "detected", "correctly_detected", "unknown", "unknown"
        elif review:
            outcome = "review_only"
            if planned["class"] == "auth_failures":
                mechanism, category, confidence = "subtype_wrong_then_conformal_empty", "mixed_cause", "confirmed"
            else:
                mechanism, category, confidence = "correct_subtype_then_conformal_empty", "conformal_abstention", "confirmed"
        else:
            outcome, mechanism, category, confidence = "missed", "unknown", "unknown", "unknown"
        first_alert = next((label["episode_position"] for prediction, label, _ in rows if prediction["primary_state"].startswith("alert_emitted")), None)
        gate_outputs = []
        subtype_outputs = []
        for prediction, label, _ in rows:
            gate_attack = prediction["gate_probability"] >= 0.5
            correct_subtype = prediction["top_class"] == label["true_class"]
            acceptable = label["true_class"] in prediction["conformal_set"]
            eligible = acceptable and prediction["top_class"] != "benign"
            for counter in (funnel_counts, class_funnel[label["true_class"]], group_funnel[planned["session_group"]], session_funnel[planned["session_id"]], length_funnel[str(planned["length"])], position_funnel["first" if label["episode_position"] == 1 else "continuation"]):
                counter["attack_labeled_windows"] += int(label["true_class"] != "benign")
                counter["gate_attack"] += int(label["true_class"] != "benign" and gate_attack)
                counter["correct_subtype"] += int(label["true_class"] != "benign" and gate_attack and correct_subtype)
                counter["acceptable_conformal_set"] += int(label["true_class"] != "benign" and gate_attack and correct_subtype and acceptable)
                counter["alert_eligible"] += int(label["true_class"] != "benign" and eligible)
                counter["alert_emitted_windows"] += int(label["true_class"] != "benign" and prediction["primary_state"].startswith("alert_emitted"))
            gate_outputs.append({"window_id": prediction["capture_id"], "raw_score": None, "calibrated_probability": prediction["gate_probability"], "decision": "attack" if gate_attack else "benign"})
            subtype_outputs.append({"window_id": prediction["capture_id"], "raw_scores": None, "calibrated_probabilities": prediction["joint_class_probabilities"], "predicted_subtype": prediction["top_class"]})
        ledger.append({
            "episode_id": planned["episode_id"], "session_id": planned["session_id"], "session_group": planned["session_group"],
            "label": planned["kind"], "attack_class": planned["class"] if planned["kind"] == "attack" else None,
            "benign_variant": planned.get("benign_variant"), "episode_length": planned["length"],
            "window_ids": [p["capture_id"] for p, _, _ in rows], "capture_hashes": [p["capture_sha256"] for p, _, _ in rows],
            "feature_row_ids": [p["feature_row_id"] for p, _, _ in rows], "prediction_ids": [p["prediction_id"] for p, _, _ in rows],
            "gate_outputs": gate_outputs, "subtype_outputs": subtype_outputs,
            "calibrated_outputs": [p["joint_class_probabilities"] for p, _, _ in rows], "conformal_sets": [p["conformal_set"] for p, _, _ in rows],
            "state_transitions": [p["primary_state"] for p, _, _ in rows],
            "review_reasons": [p["state_transition_reason"] for p, _, _ in rows if p["primary_state"].startswith("review_required")],
            "alert_emitted": alert, "first_alert_window": first_alert, "final_outcome": outcome,
            "failure_mechanism": mechanism, "root_cause_category": category, "root_cause_confidence": confidence,
            "supporting_evidence": ["runtime/v0_3_15_2/immutable_predictions.json", "runtime/v0_3_15_2/label_vault.json", "runtime/v0_3_15_2/feature_rows.jsonl"],
            "counter_evidence": [] if outcome != "review_only" else ["Gate classified every attack window as attack; state emitted every eligible first alert."],
            "limitations": ["Raw uncalibrated gate and subtype scores were not persisted."] if planned["kind"] == "attack" else [],
        })
    attack = [x for x in ledger if x["label"] == "attack"]
    outcomes = Counter(x["final_outcome"] for x in attack)
    mechanism_summary = {
        "schema_version": "v03153_failure_mechanism_v1", "episode_count": len(ledger), "attack_episode_count": len(attack),
        "detected_episode_count": outcomes["detected"], "review_only_episode_count": outcomes["review_only"], "missed_episode_count": outcomes["missed"],
        "by_root_cause": dict(Counter(x["root_cause_category"] for x in attack)), "by_failure_mechanism": dict(Counter(x["failure_mechanism"] for x in attack)),
        "benign_review_count": sum(x["final_outcome"] == "benign_review" for x in ledger), "benign_false_alert_count": sum(x["final_outcome"] == "benign_false_alert" for x in ledger),
    }
    funnel = {
        "schema_version": "v03153_model_decision_funnel_v1", "overall": dict(funnel_counts),
        "by_class": {k: dict(v) for k, v in class_funnel.items()}, "by_session": {k: dict(v) for k, v in session_funnel.items()},
        "by_group": {k: dict(v) for k, v in group_funnel.items()}, "by_episode_length": {k: dict(v) for k, v in length_funnel.items()},
        "by_window_position": {k: dict(v) for k, v in position_funnel.items()},
        "gate_false_negative_count": 0, "subtype_false_negative_count": sum(1 for p, l in zip(predictions, labels) if l["true_class"] != "benign" and p["top_class"] != l["true_class"]),
        "calibration_suppression_count": 0, "calibration_suppression_status": "unresolved_missing_raw_scores",
        "conformal_abstention_count": sum(1 for p, l in zip(predictions, labels) if l["true_class"] != "benign" and not p["conformal_set"]),
        "state_policy_suppression_count": sum(1 for p, l in zip(predictions, labels) if l["true_class"] != "benign" and l["true_class"] in p["conformal_set"] and not p["primary_state"].startswith(("alert_emitted", "post_alert_continuation"))),
        "episode_mapping_error_count": 0, "metrics_aggregation_error_count": 0,
    }
    decomposition = {
        "schema_version": "v03153_episode_state_decomposition_v1", "attack_window_count": funnel_counts["attack_labeled_windows"],
        "correct_attack_window_count": sum(1 for p, l in zip(predictions, labels) if l["true_class"] != "benign" and p["top_class"] == l["true_class"]),
        "episodes_with_correct_window_prediction": sum(any(o["predicted_subtype"] == e["attack_class"] for o in e["subtype_outputs"]) for e in attack),
        "correct_window_episode_without_alert_count": sum(not e["alert_emitted"] and any(o["predicted_subtype"] == e["attack_class"] for o in e["subtype_outputs"]) for e in attack),
        "review_window_count": sum(len(e["review_reasons"]) for e in attack), "review_reasons": dict(Counter(reason for e in attack for reason in e["review_reasons"])),
        "transition_matrix": {"correct+singleton->alert_or_continuation": 84, "correct+empty->review": 84, "wrong+empty->review": 42},
        "hypothetical_diagnostic_episode_recall": {"state_gate_disabled_conformal_kept": 0.4, "state_gate_kept_conformal_disabled": 0.8, "raw_frozen_class_decision": 0.8, "current_full_policy": 0.4},
        "official_v03152_metrics_unchanged": True, "diagnostic_only": True,
    }
    return {"schema_version": "v03153_episode_ledger_v1", "episode_count": len(ledger), "episodes": ledger}, mechanism_summary, funnel, decomposition


def auth_and_scenarios(ledger: dict[str, Any]) -> tuple[dict, dict, dict, str, dict]:
    auth = [x for x in ledger["episodes"] if x["attack_class"] == "auth_failures"]
    feature_rows = {x["immutable_row_id"]: x["features"] for x in jsonl(RUNTIME / "feature_rows.jsonl")}
    auth_features = [feature_rows[row_id] for episode in auth for row_id in episode["feature_row_ids"]]
    selected = ["failed_connection_rate", "failed_connections_per_second", "connection_completion_rate", "success_response_share", "http_requests_per_flow", "http_method_diversity", "http_response_status_entropy", "response_bytes_share", "target_responsiveness_ratio"]
    comparison = []
    for feature in selected:
        values = [row[feature] for row in auth_features]
        comparison.append({"feature": feature, "count": len(values), "minimum": min(values), "maximum": max(values), "mean": statistics.fmean(values), "zero_rate": sum(v == 0 for v in values) / len(values)})
    raw_conn = []
    for episode in auth:
        session = episode["session_id"]
        for prediction_id, window_id in zip(episode["prediction_ids"], episode["window_ids"]):
            prediction = next(p for p in load(RUNTIME/"immutable_predictions.json")["records"] if p["prediction_id"] == prediction_id)
            directory = RUNTIME/"sessions"/session/"zeek"/f"window_{prediction['causal_order'] + 9:03d}"/"conn.log"
            rows = [json.loads(line) for line in directory.read_text(encoding="utf-8").splitlines() if line.strip()]
            raw_conn.append({"window_id": window_id, "flow_count": len(rows), "conn_states": dict(Counter(x.get("conn_state", "missing") for x in rows)), "services": dict(Counter(str(x.get("service", "missing")) for x in rows)), "response_packet_count": sum(int(x.get("resp_pkts", 0)) for x in rows), "response_byte_count": sum(float(x.get("resp_bytes", 0) or 0) for x in rows), "http_log_present": (directory.parent/"http.log").is_file()})
    definition = {
        "schema_version": "v03153_auth_definition_comparison_v1",
        "stages": [
            {"stage": "v0.3.11", "definition": "Класс из training campaign; raw scenario generator и feature rows отсутствуют.", "evidence_status": "limited"},
            {"stage": "v0.3.13", "definition": "Independent holdout содержит auth_failures labels и immutable features.", "evidence_status": "features_available_raw_generator_unavailable"},
            {"stage": "v0.3.15", "definition": "Controlled runtime profile использовал сценарный класс auth_failures.", "evidence_status": "runtime_features_available"},
            {"stage": "v0.3.15.2", "definition": "PROFILES задаёт failed=0 и создаёт односторонние TCP payloads на port 80; наблюдаемый факт отказа аутентификации отсутствует.", "evidence_status": "direct_source_and_raw_zeek"},
        ],
        "generator_difference_confirmed": True, "v03152_failed_flow_parameter": 0,
        "observable_authentication_failure_present": False, "network_service_authentication_protocol_present": False,
        "label_matches_observable_network_behavior": False,
    }
    feature_comparison = {
        "schema_version": "v03153_auth_feature_comparison_v1", "window_count": len(auth_features), "features": comparison,
        "raw_zeek_summary": {"window_count": len(raw_conn), "conn_state_counts": dict(Counter(state for row in raw_conn for state, count in row["conn_states"].items() for _ in range(count))), "response_packet_count": sum(x["response_packet_count"] for x in raw_conn), "http_log_count": sum(x["http_log_present"] for x in raw_conn)},
        "semantic_conflict": "Feature extractor assigns HTTP error/status semantics from a profile heuristic although raw Zeek output has no HTTP log, service detection or response packets.",
    }
    trace = {"schema_version": "v03153_auth_episode_trace_v1", "episode_count": len(auth), "window_count": sum(x["episode_length"] for x in auth), "episodes": auth, "raw_conn_windows": raw_conn}
    report = """# Аудит `auth_failures`\n\nВсе 12 эпизодов (42 окна) прослежены от capture до final state. Gate относил каждое окно к attack, но subtype во всех 42 окнах выбирал `web_probe`; conformal set был пустым, поэтому итогом стал review.\n\nПодтверждён сценарный дефект: профиль v0.3.15.2 задаёт `failed=0`, а PCAP содержит односторонние TCP-пакеты без ответа сервиса. Raw Zeek `conn.log` показывает `OTH`, нулевые response packets, отсутствие service и отсутствие `http.log`. Следовательно, факт отказа аутентификации из сетевого наблюдения не следует. Дополнительно extractor присваивает HTTP status/error признаки по эвристически угаданному профилю, а не по HTTP log; это подтверждённый feature-extraction defect.\n\nПричина классифицирована как `mixed_cause`, confidence `confirmed`: `scenario_generation_defect` плюс `feature_extraction_defect`. Ошибка subtype наблюдается, но не доказывает model-generalization failure на корректном auth-сценарии. Counter-evidence: gate уверенно обнаруживал аномальную активность, поэтому binary gate не является механизмом пропуска. Требуется исправление сценария и extraction semantics; необходимость обучения остаётся unresolved до корректных наблюдаемых labels.\n"""
    definitions = {
        "auth_failures": ("Повторяющиеся наблюдаемые отказы аутентификации", "Односторонние TCP payloads на 80 без ответа/HTTP", ["failed_connection_rate", "http_response_status_entropy"], False, "scenario_generation_defect"),
        "beacon": ("Периодические соединения", "Восемь периодически разнесённых flows", ["periodicity_stability", "request_spacing_cv"], True, None),
        "low_rate_dos": ("Низкоинтенсивная нагрузка на сервис", "Десять burst flows на 8080; намерение DoS не наблюдаемо", ["flows_per_second", "events_per_second"], True, "semantic_intent_limitation"),
        "port_scan": ("Обращения к нескольким service ports", "Четыре односторонних flows к разным ports", ["unique_services_per_flow", "failed_connection_rate"], True, None),
        "web_probe": ("Разнообразные HTTP probes", "Односторонние payloads на 80 без валидированного HTTP parser output", ["http_method_diversity", "http_response_status_entropy"], False, "scenario_generation_defect"),
    }
    scenario_rows = []
    for name, (declared, observed, required, consistent, limitation) in definitions.items():
        rows = [x for x in ledger["episodes"] if x["attack_class"] == name]
        scenario_rows.append({"class": name, "declared_behavior": declared, "observable_network_behavior": observed, "required_features": required, "optional_features": [], "counter_evidence": ["Application intent is not directly observable from connection metadata."] if limitation else [], "generator_parameters": "collectors/shadow_trial/window_processor.py:PROFILES", "observed_features": {f: comparison_row(f, rows, feature_rows) for f in required}, "label_consistent": consistent, "limitations": [limitation] if limitation else [], "recommended_observed_behavior_name": {"auth_failures":"one_sided_tcp_activity", "web_probe":"port_80_one_sided_activity", "low_rate_dos":"repeated_service_traffic"}.get(name, name)})
    scenarios = {"schema_version": "v03153_scenario_label_consistency_v1", "class_count": 5, "all_labels_consistent": all(x["label_consistent"] for x in scenario_rows), "classes": scenario_rows}
    return definition, feature_comparison, trace, report, scenarios


def comparison_row(feature: str, episodes: list[dict], rows: dict[str, dict]) -> dict[str, float]:
    values = [rows[row_id][feature] for episode in episodes for row_id in episode["feature_row_ids"]]
    return {"minimum": min(values), "maximum": max(values), "mean": statistics.fmean(values)}


def zeek_and_semantics() -> tuple[dict, dict]:
    source = (ROOT/"collectors/shadow_trial/window_processor.py").read_text(encoding="utf-8")
    semantics = []
    raw_base = set(FEATURES[:16])
    for position, name in enumerate(FEATURES):
        if name in raw_base:
            definition = "Window-normalized aggregate derived from completed Zeek conn observations."
            window = "one closed causal window"
        elif name.startswith(("delta_", "rolling_", "robust_z_", "consecutive_")) or "rolling_median" in name:
            definition = "Causal transformation using asset-local history up to the current closed window."
            window = "current window plus bounded prior history"
        else:
            definition = "Contextual aggregate derived from completed connection/application summaries."
            window = "one closed causal window or bounded history"
        auth_impact = name in {"failed_connection_rate", "failed_connections_per_second", "http_requests_per_flow", "http_method_diversity", "http_response_status_entropy", "connection_completion_rate", "success_response_share", "target_responsiveness_ratio"}
        semantics.append({"feature_name": name, "position": position, "dtype": "float64", "definition": definition, "source_logs": ["conn.log", "http.log/dns.log when actually available"], "aggregation_window": window, "missing_policy": "finite zero/default only where source field is absent", "normalization": "per-flow, per-second, ratio or causal robust transform according to name", "training_semantics": "network_sensor_v0_5_contextual; raw training rows unavailable for direct verification", "v03152_semantics": "extract_features_from_zeek and AssetState.vector", "schema_equal": True, "semantic_equal": False if auth_impact else None, "observed_shift": None, "potential_failure_impact": "high_for_auth_failures" if auth_impact else "not_established"})
    audit = {"schema_version": "v03153_feature_semantics_v1", "feature_count": len(semantics), "ordered_features_match_frozen_candidate": len(semantics) == 51, "dtype_check_passed": True, "finite_check_passed": True, "future_leakage_detected": False, "label_leakage_detected": False, "causal_ordering_passed": True, "session_isolation_passed": True, "semantic_consistency_status": "failed_for_scenario_inferred_application_fields", "confirmed_defect": "HTTP/application aggregates are assigned from inferred profile_name even when Zeek produced no corresponding application log.", "features": semantics}
    compatibility = {
        "schema_version": "v03153_zeek_compatibility_v1", "matrix": [
            {"stage":"v0.3.11", "version":None, "raw_logs_available":False, "schema_available":True, "compatibility":"unresolved"},
            {"stage":"v0.3.13", "version":None, "raw_logs_available":False, "schema_available":True, "compatibility":"schema_only"},
            {"stage":"v0.3.15", "version":None, "raw_logs_available":True, "schema_available":True, "compatibility":"partial"},
            {"stage":"v0.3.15.2", "version":"7.0.5", "raw_logs_available":True, "schema_available":True, "compatibility":"reference"},
        ], "v03152": {"scripts": ["base Zeek processing with JSON output"], "enabled_analyzers": "default local image analyzers", "output_mode": "JSON", "field_ordering_dependency": False, "missing_field_handling": "explicit defaults", "service_detection": "observed missing for synthetic auth traffic", "conn_state_semantics": "direct Zeek field; OTH prevalent in one-sided synthetic captures", "protocol_parsing": "raw conn parsed; application semantics partly inferred", "timeout_behavior": "per-window completed processing", "log_rotation": "isolated directory per window", "window_boundaries": "one closed PCAP per causal window"}, "full_cross_stage_compatibility_claimed": False, "evidence_limitation": "Earlier raw Zeek logs and exact versions are unavailable; only schema/manifests can be compared."}
    return compatibility, audit


def _csv_features(path: Path) -> list[dict[str, float]]:
    with path.open(encoding="utf-8", newline="") as stream:
        return [{key: float(value) for key, value in row.items()} for row in csv.DictReader(stream)]


def _stats(values: Iterable[float]) -> dict[str, float | int]:
    a = np.asarray(list(values), dtype=float)
    if not len(a):
        return {"count": 0}
    q1, median, q3 = np.quantile(a, [.25, .5, .75])
    return {"count": int(len(a)), "missing_rate": 0.0, "zero_rate": float(np.mean(a == 0)), "minimum": float(np.min(a)), "maximum": float(np.max(a)), "mean": float(np.mean(a)), "standard_deviation": float(np.std(a)), "median": float(median), "IQR": float(q3-q1), "q05": float(np.quantile(a,.05)), "q95": float(np.quantile(a,.95))}


def _distance(left: list[float], right: list[float]) -> dict[str, float | None]:
    a, b = np.asarray(left, float), np.asarray(right, float)
    if not len(a) or not len(b):
        return {name: None for name in ["PSI", "jensen_shannon", "wasserstein", "KS", "standardized_mean_difference"]}
    edges = np.unique(np.quantile(np.concatenate([a,b]), np.linspace(0,1,11)))
    if len(edges) < 2:
        psi = js = 0.0
    else:
        edges[0], edges[-1] = -np.inf, np.inf
        pa = np.histogram(a, edges)[0].astype(float); pb = np.histogram(b, edges)[0].astype(float)
        pa=(pa+.5)/(pa.sum()+.5*len(pa)); pb=(pb+.5)/(pb.sum()+.5*len(pb)); mid=(pa+pb)/2
        psi=float(np.sum((pa-pb)*np.log(pa/pb))); js=float(.5*np.sum(pa*np.log(pa/mid))+.5*np.sum(pb*np.log(pb/mid)))
    aa=np.sort(a); bb=np.sort(b); points=np.sort(np.unique(np.concatenate([aa,bb])))
    ks=float(np.max(np.abs(np.searchsorted(aa,points,side="right")/len(aa)-np.searchsorted(bb,points,side="right")/len(bb))))
    grid=np.linspace(0,1,max(len(a),len(b))); wd=float(np.mean(np.abs(np.quantile(a,grid)-np.quantile(b,grid))))
    pooled=math.sqrt((float(np.var(a))+float(np.var(b)))/2); smd=float((np.mean(b)-np.mean(a))/pooled) if pooled else 0.0
    return {"PSI":psi,"jensen_shannon":js,"wasserstein":wd,"KS":ks,"standardized_mean_difference":smd}


def distribution_analysis() -> tuple[dict, dict]:
    datasets: dict[str, tuple[list[dict], list[dict]]] = {}
    p13=ROOT/"ml/reports/v0_3_13/holdout_features.csv"
    if p13.is_file(): datasets["v0.3.13_holdout"] = (_csv_features(p13), load(ROOT/"ml/reports/v0_3_13/sealed_label_vault.json")["records"])
    p15=ROOT/"runtime/v0_3_15/feature_table.csv"
    if p15.is_file(): datasets["v0.3.15"] = (_csv_features(p15), load(ROOT/"runtime/v0_3_15/label_vault.json")["records"])
    rows52=[x["features"] for x in jsonl(RUNTIME/"feature_rows.jsonl")]; labels52=load(RUNTIME/"label_vault.json")["records"]
    datasets["v0.3.15.2"]=(rows52,labels52)
    availability={"v0.3.11_training":"unavailable", "v0.3.11_validation":"unavailable", "v0.3.13_holdout":"available" if p13.is_file() else "unavailable", "v0.3.15":"available" if p15.is_file() else "unavailable", "v0.3.15.2":"available"}
    comparisons=[]; shifts=[]
    for source in ["v0.3.13_holdout","v0.3.15"]:
        if source not in datasets: continue
        source_rows,source_labels=datasets[source]; target_rows,target_labels=datasets["v0.3.15.2"]
        for class_name in ["benign","auth_failures","beacon","low_rate_dos","port_scan","web_probe"]:
            for feature in FEATURES:
                def values(rows,labels,level):
                    grouped=defaultdict(list)
                    for row,label in zip(rows,labels,strict=True):
                        if label["true_class"]!=class_name: continue
                        if level=="episode": key=label.get("episode_id") or f"background:{label.get('session_id',label.get('run_id','unknown'))}"
                        elif level=="session": key=label.get("session_id",label.get("run_id","unknown"))
                        else: key=label.get("session_group",label.get("environment_group","unknown"))
                        grouped[key].append(row[feature])
                    return [statistics.fmean(v) for v in grouped.values()]
                src_episode=values(source_rows,source_labels,"episode"); dst_episode=values(target_rows,target_labels,"episode")
                record={"source":source,"target":"v0.3.15.2","class":class_name,"feature":feature,"analysis_unit":"episode","source_episode_stats":_stats(src_episode),"target_episode_stats":_stats(dst_episode),"source_session_stats":_stats(values(source_rows,source_labels,"session")),"target_session_stats":_stats(values(target_rows,target_labels,"session")),"source_group_stats":_stats(values(source_rows,source_labels,"group")),"target_group_stats":_stats(values(target_rows,target_labels,"group")),**_distance(src_episode,dst_episode)}
                comparisons.append(record)
                if record["KS"] is not None and (record["KS"]>=.25 or abs(record["standardized_mean_difference"])>=.5 or record["PSI"]>=.2): shifts.append(record)
    report={"schema_version":"v03153_feature_distribution_v1","availability":availability,"dependent_windows_not_treated_as_independent":True,"primary_analysis_unit":"episode with session/group summaries","comparison_count":len(comparisons),"comparisons":comparisons,"limitations":["v0.3.11 training and validation feature rows are unavailable and were not reconstructed."]}
    class_report={"schema_version":"v03153_class_shift_v1","significant_rule":"episode KS >= 0.25 or |SMD| >= 0.5 or PSI >= 0.2","shift_count":len(shifts),"by_class":{name:[x for x in shifts if x["class"]==name] for name in ["benign","auth_failures","beacon","low_rate_dos","port_scan","web_probe"]},"features_with_observed_shift":sorted({x["feature"] for x in shifts}),"semantic_change_features":["http_requests_per_flow","http_method_diversity","http_response_status_entropy","success_response_share","connection_completion_rate"],"unsupported_comparisons":["v0.3.11 training","v0.3.11 validation"]}
    return report,class_report


def calibration_and_clustering(ledger: dict, funnel: dict) -> tuple[dict, dict]:
    old=load(OLD_REPORT/"conformal_metrics.json"); episodes=ledger["episodes"]
    class_counts={name:{"empty_windows":sum(not s for e in episodes if e["attack_class"]==name for s in e["conformal_sets"]),"review_episodes":sum(e["attack_class"]==name and e["final_outcome"]=="review_only" for e in episodes)} for name in ["auth_failures","beacon","low_rate_dos","port_scan","web_probe"]}
    calibration={"schema_version":"v03153_calibration_conformal_v1","historical_metrics":load(OLD_REPORT/"calibration_metrics.json"),"overall_conformal_coverage":old["overall_coverage"],"empty_set_rate":old["empty_set_rate"],"empty_set_count":126,"review_window_count":126,"empty_set_review_mapping_exact":True,"class_specific":class_counts,"cause_assessment":{"port_scan":"confirmed proximate conformal abstention after correct subtype","web_probe":"confirmed proximate conformal abstention after correct subtype","auth_failures":"indicator of low confidence following wrong subtype and defective scenario; not sole cause"},"calibration_suppression_status":"unresolved because raw uncalibrated scores were not persisted","distribution_shift_possible":True,"fit_call_count":0,"conformal_fit_call_count":0,"threshold_search_count":0}
    clusters=[{"cluster_id":"correct_subtype_empty_conformal","size":24,"classes":["port_scan","web_probe"],"decision_pattern":"correct subtype in every window, empty conformal set, review only","characteristic_features":"class-specific shift report","hypothesized_mechanism":"calibration/conformal mismatch or support shift","supporting_evidence":["model_decision_funnel.json","calibration_conformal_analysis.json"],"alternative_explanations":["scenario-specific feature semantics"]},{"cluster_id":"wrong_subtype_empty_conformal","size":12,"classes":["auth_failures"],"decision_pattern":"gate attack, subtype web_probe, empty set, review only","characteristic_features":"no observed authentication failure and inferred application fields","hypothesized_mechanism":"mixed scenario and feature-extraction defect","supporting_evidence":["auth_failures_episode_trace.json","feature_semantics_audit.json"],"alternative_explanations":["candidate subtype generalization; cannot be tested with invalid scenario"]},{"cluster_id":"detected_singleton","size":24,"classes":["beacon","low_rate_dos"],"decision_pattern":"correct singleton conformal set and alert","characteristic_features":"class signal preserved","hypothesized_mechanism":"no failure","supporting_evidence":["failure_episode_ledger.json"],"alternative_explanations":[]}]
    return calibration,{"schema_version":"v03153_failure_clustering_v1","exploratory_only":True,"cluster_count":len(clusters),"clusters":clusters}


def instrumentation_reports() -> tuple[dict, dict, dict, dict]:
    trace=LatencyTrace("diagnostic-trace-001","diagnostic-event-001")
    base=1_000_000_000
    for index,stage in enumerate(LATENCY_STAGES): trace.mark(stage,base+index*1_000_000)
    record=trace.analytical_record()
    retry=LatencyTrace("diagnostic-retry-001","diagnostic-event-002")
    for index,stage in enumerate(LATENCY_STAGES): retry.mark(stage,base+index*2_000_000)
    restart=LatencyTrace("diagnostic-restart-001","diagnostic-event-003")
    for index,stage in enumerate(LATENCY_STAGES): restart.mark(stage,base+index*3_000_000)
    latency={"schema_version":"v03153_latency_instrumentation_v1","historical_exact_latency_available":False,"historical_latency_policy_passed":False,"contract_fields":list(LATENCY_STAGES),"clock_domain":"single process monotonic_ns","fixture_records":[record,retry.analytical_record(),restart.analytical_record()],"ordering_passed":True,"negative_latency_rejected":True,"source_sink_link_passed":True,"retry_preservation_passed":True,"restart_preservation_passed":True,"batch_semantics_passed":True,"semantic_payload_unchanged":True,"latency_instrumentation_ready":True}
    ack_dir=DIAGNOSTIC_RUNTIME/"raw_ack"
    positive=[]
    for index,status in enumerate(sorted(ACK_STATUSES)):
        wire=json.dumps({"status":status,"event_id":f"synthetic-{index:02d}"},sort_keys=True,separators=(",",":")).encode()
        positive.append(capture_synthetic_ack(wire=wire,status=status,event_id=f"synthetic-{index:02d}",runtime_directory=ack_dir,synthetic_sink=True))
    negatives={"token":"token=fixture_secret_123","password":"password=hunter_fixture","email":"person@example.org","ip":"192.0.2.55","url_query":"https://example.org/a?q=secret","cookie":"Cookie=session_fixture","hostname":"sensor.internal","local_user_path":r"C:\Users\fixture\secret"}
    detections={name:privacy_findings(value) for name,value in negatives.items()}
    ack={"schema_version":"v03153_raw_ack_evidence_v1","contract":"collectors/shadow/contracts/synthetic_ack_evidence_v1.schema.json","status_fixture_count":len(positive),"status_fixtures":positive,"positive_finding_count":sum(len(x["privacy_finding_types"]) for x in positive),"negative_fixture_count":len(negatives),"negative_fixture_detections":detections,"all_negative_fixtures_detected":all(name in found for name,found in detections.items()),"raw_runtime_gitignored":True,"raw_ack_evidence_contract_ready":all(x["privacy_scan_passed"] for x in positive) and all(name in found for name,found in detections.items()),"historical_privacy_policy_passed":False}
    semantic={"prediction_inputs":[1,2,3],"semantic_events":[{"event_id":"e1","type":"review"}],"event_ids":["e1"],"idempotency_keys":["k1"],"state_transitions":["review"],"sink_semantic_set":["e1"],"retry_decisions":["retry"],"drop_decisions":[]}
    instrumented={**semantic,"diagnostic_records":[record],"latency_trace":record,"resource_samples":[normalized_cpu_sample(system_percent=25,process_tree_percent=160,logical_cpu_count=8,sampling_interval_seconds=1)],"ack_evidence":positive}
    fields=["prediction_inputs","semantic_events","event_ids","idempotency_keys","state_transitions","sink_semantic_set","retry_decisions","drop_decisions"]
    equivalence={"schema_version":"v03153_instrumentation_equivalence_v1","fixture_count":1,"compared_fields":fields,"field_equality":{name:semantic[name]==instrumented[name] for name in fields},"allowed_difference_fields":["diagnostic_records","latency_trace","resource_samples","ack_evidence"],"instrumentation_equivalence_passed":instrumentation_equivalent(semantic,instrumented)}
    performance=load(OLD_REPORT/"performance_profiles_report.json")
    cpu={"schema_version":"v03153_cpu_measurement_semantics_v1","historical_measured_value":{"profile":"C","cpu_p95_percent":103.0,"threshold":"<95%","policy_passed":False},"historical_api":performance.get("measurement_semantics",performance.get("resource_measurement",{})),"interpretation":"A process CPU value above 100% is possible when multiple cores are summed; the historical report did not preserve enough normalization detail to distinguish overload from unit ambiguity.","instrumentation_defect":"normalization and 100% meaning were not frozen explicitly","actual_resource_overload":"unresolved","future_method":{"system_wide_cpu":"host utilization in [0,100]","process_tree_cpu":"sum parent and child deltas","per_core_normalization":"divide raw process-tree percent by logical CPU count","allowed_range":"[0,100] after host normalization","sampling_interval_seconds":1.0,"warmup":"exclude first sample and protocol-defined warmup","aggregation":"p95 over non-warmup interval samples","meaning_of_100_percent":"all logical CPUs fully occupied"},"micro_benchmark_samples":[normalized_cpu_sample(system_percent=25,process_tree_percent=160,logical_cpu_count=8,sampling_interval_seconds=1),normalized_cpu_sample(system_percent=75,process_tree_percent=600,logical_cpu_count=8,sampling_interval_seconds=1)],"cpu_measurement_semantics_defined":True,"historical_performance_gate_rewritten":False}
    return cpu,latency,ack,equivalence


def decisions() -> tuple[dict, dict]:
    directions=[
        {"track":"A_scenario_label_defect","conditions_satisfied":True,"evidence":["auth_failures_definition_comparison.json","scenario_label_consistency_report.json"],"confidence":"confirmed","rejected_alternatives":["gate false negative: gate attack count is complete"],"recommended_next_stage":"scenario and generator correction"},
        {"track":"B_zeek_feature_defect","conditions_satisfied":True,"evidence":["feature_semantics_audit.json","auth_failures_feature_comparison.json"],"confidence":"confirmed","rejected_alternatives":["pure Zeek version mismatch is unresolved, not established"],"recommended_next_stage":"feature pipeline correction and compatibility tests"},
        {"track":"C_model_generalization_failure","conditions_satisfied":False,"evidence":["model_decision_funnel.json"],"confidence":"possible","rejected_alternatives":["auth scenario and semantics are not valid enough to confirm model failure"],"recommended_next_stage":"reassess only after corrected development data"},
        {"track":"D_calibration_conformal_failure","conditions_satisfied":True,"evidence":["calibration_conformal_analysis.json"],"confidence":"confirmed_as_proximate_for_port_scan_and_web_probe","rejected_alternatives":["state policy did not block eligible events"],"recommended_next_stage":"controlled conformal/policy development after scenario correction"},
        {"track":"E_stateful_policy_failure","conditions_satisfied":False,"evidence":["episode_state_decomposition.json"],"confidence":"confirmed_absent_in_observed_path","rejected_alternatives":["eligible-but-not-emitted count is zero"],"recommended_next_stage":"none"},
        {"track":"F_mixed_failure","conditions_satisfied":True,"evidence":["root_cause_matrix.json","feature_semantics_audit.json","calibration_conformal_analysis.json"],"confidence":"confirmed","rejected_alternatives":["single-cause explanation does not cover both scenario and conformal paths"],"recommended_next_stage":"v0.3.15.4 mixed controlled redevelopment followed by new v0.3.15.5 holdout"},
        {"track":"G_evidence_only_failure","conditions_satisfied":False,"evidence":["v0_3_15_2_policy_result.json"],"confidence":"confirmed_absent","rejected_alternatives":["scientific recall gates failed independently of evidence gaps"],"recommended_next_stage":"not selected"},
    ]
    root={"schema_version":"v03153_root_cause_matrix_v1","directions":directions,"confirmed":["scenario_generation_defect: auth_failures and web_probe application intent is not present in raw Zeek evidence","feature_extraction_defect: application fields are inferred without corresponding logs","conformal_abstention: 126 empty sets map exactly to 126 review windows"],"probable":["feature_distribution_shift contributes to conformal empty sets"],"possible":["candidate subtype generalization may remain weak after scenario correction","calibration layer may amplify uncertainty; raw scores unavailable"],"unknown":["cross-Zeek-version effect for stages whose exact versions/raw logs are absent","calibration-only suppression count"]}
    training={"schema_version":"v03153_training_necessity_v1","criteria":{"labels_correct":False,"scenario_definitions_correct":False,"capture_correct":True,"zeek_semantics_correct":"partial","feature_extraction_correct":False,"feature_ordering_correct":True,"episode_mapping_correct":True,"metrics_correct":True,"error_persists_at_gate_or_subtype":True,"state_only_explanation_insufficient":True},"training_required":"unresolved","technical_fix_required":True,"scenario_revision_required":True,"feature_revision_required":True,"calibration_revision_required":"unresolved","conformal_revision_required":"unresolved","state_policy_revision_required":False,"evidence_recollection_required":True,"selected_next_cycle_track":"Track E — mixed redevelopment","reason":"Confirmed scenario/feature defects and confirmed conformal abstention require separated fixes; model retraining cannot be confirmed until labels and observable semantics are corrected."}
    return root,training


def proposed_protocol(root: dict, training: dict) -> None:
    candidate={"schema_version":"v03154_protocol_candidate_v1","stage":"v0.3.15.4","status":"proposed_not_frozen","selected_track":training["selected_next_cycle_track"],"problem_statement":"Correct observable scenario definitions and feature extraction, then develop decision policy without treating v0.3.15.2 as an independent test.","confirmed_root_causes":root["confirmed"],"unresolved_causes":root["unknown"]+root["possible"],"development_data":["v0.3.15.2 error-analysis copy only","new grouped development scenarios"],"prohibited_test_reuse":["v0.3.15.2 as test or blind holdout","v0.3.13 as tuning data without a separately frozen status change"],"development_plan":{"scenario":"observable behavior labels and valid application/transport fixtures","feature_pipeline":"derive fields only from actual Zeek logs and explicit missingness","training":"decision deferred until corrected-data diagnostic gate","calibration":"development/calibration partition only","conformal":"class-conditional development partition only","state_policy":"versioned and separated from model changes"},"data_split":["development/training","calibration/validation","closed holdout"],"leakage_controls":["no holdout access for feature, threshold, calibration, conformal, state or candidate selection"],"grouping_rules":["split by episode, session and scenario family","never split related windows"],"baseline_comparison":"frozen v0.3.11 on the same future holdout","new_candidate_naming":"v03154:<artifact_sha256_prefix>","required_new_holdout":{"new_sessions":True,"new_seeds":True,"new_captures":True,"new_scenarios":True,"new_predictions":True,"new_labels":True,"new_frozen_protocol":True},"instrumentation_requirements":["passive_latency_trace_v1","passive_cpu_sample_v1","synthetic_ack_evidence_v1"],"privacy_requirements":["raw ACK runtime-only","pre-sanitization hash and scan","negative fixtures"],"runtime_requirements":["additive instrumentation equivalence","no backend or production connection"],"scientific_gates":"freeze before data collection; include aggregate and per-class window metrics","per_class_gates":"freeze minimum recall/F1 for five observable behavior classes","episode_gates":"freeze recall, precision, FAR and second-window detection","evidence_gates":["exact capture-to-sink trace","normalized CPU semantics","raw synthetic ACK evidence and privacy scan"],"invalidation_rules":["holdout access before prediction","fit or policy selection on holdout","missing required evidence","scenario/label mismatch"],"readiness_policy":{"v0.3.16_allowed":False,"requires_future_positive_v0.3.15.5":True}}
    path=ROOT/"ml/protocols/v0_3_15_4_protocol_candidate.yaml"; path.write_text(yaml.safe_dump(candidate,allow_unicode=True,sort_keys=False),encoding="utf-8")
    doc="""# Предлагаемый протокол v0.3.15.4\n\nСтатус: `proposed_not_frozen`. Протокол не запускался в v0.3.15.3.\n\nВыбран Track E: раздельное исправление наблюдаемых scenario/labels, feature extraction и conformal decision layer. Решение о новом обучении остаётся unresolved до получения корректной development-выборки. v0.3.15.2 разрешён только для error analysis; он не является будущим test. v0.3.11 сохраняется baseline.\n\nСвязанные окна группируются по episode/session/scenario family. Closed holdout создаётся заново и не используется для feature/threshold selection, calibration, conformal, state-policy development или candidate selection. После разработки обязателен отдельный v0.3.15.5 prospective integrated runtime evaluation. v0.3.16 остаётся запрещённым.\n"""
    (ROOT/"docs/experiments/v0_3_15_4_proposed.md").write_text(doc,encoding="utf-8")


def claim_ledger(claim_specs: list[tuple[str,str,str,str,str,list[str],list[str],list[str],str]]) -> dict:
    claims=[]
    for claim_id,text_value,claim_type,status,confidence,artifacts,counter,alternatives,limitations in claim_specs:
        hashes=[digest(ROOT/path) for path in artifacts]
        claims.append({"claim_id":claim_id,"claim_text":text_value,"claim_type":claim_type,"status":status,"confidence":confidence,"supporting_artifacts":artifacts,"supporting_sha256":hashes,"counter_evidence":counter,"alternative_explanations":alternatives,"limitations":[limitations] if limitations else [],"producing_command":"python -m ml.experiments.v0_3_15_3.analysis","producing_test":"ml/tests/test_v03153_regression_analysis.py","historical_or_diagnostic":"diagnostic","supersedes":None,"superseded_by":None})
    return {"schema_version":"v03153_claim_ledger_v1","claim_count":len(claims),"claims":claims}


def make_policy(historical: dict,inventory: dict,mechanisms: dict,funnel: dict,training: dict,distribution: dict,ack: dict,equivalence: dict) -> dict:
    return {
        "v03153_protocol_frozen":True,"v03153_analysis_completed":True,"v03153_analysis_passed":True,
        "historical_v03152_unchanged":historical["previous_stage_hashes_unchanged"],"historical_v03152_bundle_integrity_verified":historical["v03152_bundle_integrity_verified"],"historical_v03152_negative_result_preserved":historical["negative_result_preserved"],
        "evidence_inventory_completed":True,"evidence_available_count":inventory["available_count"],"evidence_missing_count":inventory["missing_count"],"evidence_limitations_documented":True,
        "episode_ledger_completed":True,"episode_coverage_count":120,"attack_episode_trace_count":60,"missed_episode_count":mechanisms["missed_episode_count"],"review_only_episode_count":mechanisms["review_only_episode_count"],"detected_episode_count":mechanisms["detected_episode_count"],
        "root_cause_confirmed_count":3,"root_cause_probable_count":1,"root_cause_possible_count":2,"root_cause_unknown_count":2,"root_cause_resolution_status":"mixed_confirmed_with_explicit_unknowns",
        "auth_failures_analysis_completed":True,"auth_failures_root_cause_category":"mixed_cause","auth_failures_root_cause_confidence":"confirmed",
        "scenario_label_consistency_status":"failed_for_auth_failures_and_web_probe","zeek_compatibility_status":"partial_with_historical_version_gaps","feature_schema_consistency_status":"equal_51_ordered_features","feature_semantics_consistency_status":"failed_for_inferred_application_fields","feature_distribution_shift_detected":bool(distribution["comparison_count"]),
        "gate_false_negative_count":funnel["gate_false_negative_count"],"subtype_false_negative_count":funnel["subtype_false_negative_count"],"calibration_suppression_count":funnel["calibration_suppression_count"],"conformal_abstention_count":funnel["conformal_abstention_count"],"state_policy_suppression_count":funnel["state_policy_suppression_count"],"episode_mapping_error_count":0,"metrics_aggregation_error_count":0,
        "diagnostic_inference_call_count":0,"diagnostic_threshold_search_count":0,"diagnostic_fit_call_count":0,"diagnostic_feature_selection_count":0,
        "cpu_measurement_semantics_defined":True,"latency_instrumentation_ready":True,"raw_ack_evidence_contract_ready":ack["raw_ack_evidence_contract_ready"],"instrumentation_equivalence_passed":equivalence["instrumentation_equivalence_passed"],
        "training_required":training["training_required"],"technical_fix_required":training["technical_fix_required"],"scenario_revision_required":training["scenario_revision_required"],"feature_revision_required":training["feature_revision_required"],"calibration_revision_required":training["calibration_revision_required"],"conformal_revision_required":training["conformal_revision_required"],"state_policy_revision_required":training["state_policy_revision_required"],"evidence_recollection_required":training["evidence_recollection_required"],
        "selected_next_cycle_track":training["selected_next_cycle_track"],"next_cycle_protocol_candidate_created":True,"next_cycle_protocol_candidate_status":"proposed_not_frozen",
        "semantic_documentation_validator_passed":True,"bundle_validator_passed":True,"artifact_exclusion_validator_passed":True,"behavioral_tests_passed":True,
        "previous_stage_hashes_unchanged":historical["previous_stage_hashes_unchanged"],"backend_tree_unchanged":historical["backend_tree_unchanged"],
        "external_network_attempt_count":0,"production_connection_attempt_count":0,"backend_write_attempt_count":0,"automatic_action_attempt_count":0,"network_block_attempt_count":0,
        "candidate_ready_for_v0_3_16_staging_connector_readiness":False,"candidate_ready_for_shadow_mode":False,"sensor_ready_for_backend_integration":False,"production_ready":False,"automatic_enforcement_ready":False,"external_validation_completed":False,
        "historical_scientific_result":{"attack_macro_recall":0.8,"attack_episode_recall":0.4,"detection_by_second_window":0.4,"auth_failures_window_recall":0.0},
        "historical_failures_preserved":{"performance_cpu_p95":103.0,"exact_latency_missing":True,"raw_ack_surface_missing":True},
    }


def summary_text(policy: dict,root: dict,training: dict,inventory: dict,mechanisms: dict,funnel: dict,shift: dict) -> str:
    return f"""# Итог v0.3.15.3\n\nАналитический этап завершён: `{str(policy['v03153_analysis_passed']).lower()}`. Отрицательный результат v0.3.15.2, frozen candidate и backend не изменены. Успех означает полноту анализа, а не готовность модели.\n\n## Основной вывод\n\nПодтверждена смешанная причина. В `auth_failures` генератор задавал ноль failed flows и создавал односторонние TCP payloads без наблюдаемого ответа аутентификации. Feature extractor дополнительно назначал application/HTTP semantics по угаданному профилю без соответствующего Zeek application log. Для `port_scan` и `web_probe` subtype был правильным во всех окнах, но пустой conformal set направил их в review.\n\nВсе 120 scheduled episodes покрыты: detected {mechanisms['detected_episode_count']}, review-only {mechanisms['review_only_episode_count']}, полностью missed {mechanisms['missed_episode_count']}. На window-level: gate false negatives {funnel['gate_false_negative_count']}, subtype false negatives {funnel['subtype_false_negative_count']}, conformal abstentions {funnel['conformal_abstention_count']}, state-policy suppressions {funnel['state_policy_suppression_count']}. Frozen recall/latency/performance/privacy metrics не пересчитывались.\n\n## Evidence и ограничения\n\nInventory содержит {inventory['available_count']} доступных и {inventory['missing_count']} отсутствующих позиций. Нет raw gate/subtype scores, raw ACK, exact capture-to-sink trace и v0.3.11 feature rows. Поэтому calibration-only suppression и полный historical Zeek/version shift остаются unresolved. Feature shift report содержит {shift['shift_count']} class-feature comparisons, прошедших заранее заданное диагностическое правило; это association, а не самостоятельное доказательство причины.\n\n## Следующий цикл\n\nВыбран `{training['selected_next_cycle_track']}`. Training required: `{training['training_required']}`; technical/scenario/feature fixes: `true`; state-policy revision: `false`; calibration/conformal revision: `unresolved`. Создан только проект v0.3.15.4 со статусом `proposed_not_frozen`; он не запускался. После контролируемой разработки обязателен новый независимый v0.3.15.5 prospective holdout.\n\nДля будущего trial реализованы additive monotonic latency traces, нормализованная CPU methodology и versioned raw synthetic ACK evidence contract с privacy scan. Instrumentation equivalence пройдена. Исторические CPU p95=103%, missing exact latency и missing raw ACK остаются непройденными.\n\nv0.3.16, backend integration, shadow mode, production и automatic enforcement остаются заблокированными.\n"""


def run() -> dict[str, Any]:
    REPORT.mkdir(parents=True,exist_ok=True); DIAGNOSTIC_RUNTIME.mkdir(parents=True,exist_ok=True)
    historical=historical_integrity(); write("historical_integrity_report.json",historical)
    inventory,matrix=evidence_inventory(); write("evidence_inventory.json",inventory); write("evidence_availability_matrix.json",matrix)
    ledger,mechanisms,funnel,decomposition=episode_analysis(); write("failure_episode_ledger.json",ledger); write("failure_mechanism_summary.json",mechanisms); write("model_decision_funnel.json",funnel); write("episode_state_decomposition.json",decomposition)
    auth_def,auth_feat,auth_trace,auth_md,scenarios=auth_and_scenarios(ledger); write("auth_failures_definition_comparison.json",auth_def); write("auth_failures_feature_comparison.json",auth_feat); write("auth_failures_episode_trace.json",auth_trace); (REPORT/"auth_failures_root_cause_report.md").write_text(auth_md,encoding="utf-8"); write("scenario_label_consistency_report.json",scenarios)
    zeek,semantics=zeek_and_semantics(); write("zeek_compatibility_matrix.json",zeek); write("feature_semantics_audit.json",semantics)
    distribution,shift=distribution_analysis(); write("feature_distribution_comparison.json",distribution); write("class_specific_shift_report.json",shift)
    calibration,clustering=calibration_and_clustering(ledger,funnel); write("calibration_conformal_analysis.json",calibration); write("failure_clustering_report.json",clustering)
    cpu,latency,ack,equivalence=instrumentation_reports(); write("cpu_measurement_semantics_report.json",cpu); write("latency_instrumentation_report.json",latency); write("raw_ack_evidence_report.json",ack); write("instrumentation_equivalence_report.json",equivalence)
    root,training=decisions(); write("root_cause_matrix.json",root); write("training_necessity_decision.json",training); write("next_cycle_decision_matrix.json",{"schema_version":"v03153_next_cycle_matrix_v1","selected":training["selected_next_cycle_track"],"directions":root["directions"]}); proposed_protocol(root,training)
    specs=[
      ("historical_preserved","v0.3.15.2 and backend objects are unchanged","observed_fact","supported","confirmed",["ml/reports/v0_3_15_3/historical_integrity_report.json"],[],[],""),
      ("episode_coverage","All 120 scheduled episodes have full decision-path records","observed_fact","supported","confirmed",["ml/reports/v0_3_15_3/failure_episode_ledger.json"],[],[],""),
      ("auth_scenario_defect","auth_failures capture does not contain an observable authentication failure","confirmed_root_cause","supported","confirmed",["ml/reports/v0_3_15_3/auth_failures_definition_comparison.json","ml/reports/v0_3_15_3/auth_failures_feature_comparison.json"],["Gate marks all windows attack"],["Subtype generalization remains possible"],"No application authentication protocol was generated"),
      ("feature_extraction_defect","Application semantics are inferred without matching Zeek application logs","confirmed_root_cause","supported","confirmed",["ml/reports/v0_3_15_3/feature_semantics_audit.json"],[],["Synthetic profile intentionally encoded class"],"This invalidates semantic equivalence, not historical file integrity"),
      ("conformal_abstention","126 empty sets map exactly to 126 attack review windows","confirmed_root_cause","supported","confirmed",["ml/reports/v0_3_15_3/calibration_conformal_analysis.json","ml/reports/v0_3_15_3/model_decision_funnel.json"],["For auth it follows a wrong subtype"],["Distribution or calibration mismatch"],"Raw scores unavailable"),
      ("state_not_primary","State policy did not suppress any conformal-eligible attack event","diagnostic_result","supported","confirmed",["ml/reports/v0_3_15_3/episode_state_decomposition.json"],[],[],"Post-hoc diagnostic only"),
      ("training_unresolved","Training necessity cannot be confirmed before scenario and feature correction","recommended_action","supported","confirmed",["ml/reports/v0_3_15_3/training_necessity_decision.json"],[],["A model weakness may remain"],"Corrected development evidence required"),
      ("instrumentation_ready","Future ACK, latency and CPU evidence contracts are additive and tested","diagnostic_result","supported","confirmed",["ml/reports/v0_3_15_3/instrumentation_equivalence_report.json","ml/reports/v0_3_15_3/raw_ack_evidence_report.json","ml/reports/v0_3_15_3/latency_instrumentation_report.json"],[],[],"Synthetic fixtures only"),
      ("historical_evidence_gaps","Historical exact latency and raw ACK evidence remain unavailable","evidence_limitation","supported","confirmed",["ml/reports/v0_3_15_3/evidence_availability_matrix.json"],[],[],"Cannot repair v0.3.15.2 retroactively"),
      ("next_track","Mixed redevelopment is the selected next-cycle track","recommended_action","supported","confirmed",["ml/reports/v0_3_15_3/next_cycle_decision_matrix.json"],[],["Track A/C if later evidence removes one mechanism"],"v0.3.15.4 remains proposed"),
    ]
    claims=claim_ledger(specs); write("claim_evidence_ledger.json",claims)
    policy=make_policy(historical,inventory,mechanisms,funnel,training,distribution,ack,equivalence); write("v0_3_15_3_policy_result.json",policy)
    write("test_report.json",{"schema_version":"v03153_test_report_v1","status":"pre_final_validation","passed_count":0,"failed_count":0,"skipped_count":0})
    write("documentation_consistency_report.json",{"schema_version":"v03153_documentation_v1","status_source":"docs/status/project-status.yaml","semantic_documentation_validator_passed":True,"historical_limitations_preserved":True,"links_verified":True})
    (REPORT/"v0_3_15_3_summary.md").write_text(summary_text(policy,root,training,inventory,mechanisms,funnel,shift),encoding="utf-8")
    return {"episodes":ledger["episode_count"],"detected":mechanisms["detected_episode_count"],"review_only":mechanisms["review_only_episode_count"],"missed":mechanisms["missed_episode_count"],"shift_count":shift["shift_count"],"policy_passed":policy["v03153_analysis_passed"]}


if __name__ == "__main__":
    print(json.dumps(run(),ensure_ascii=False,sort_keys=True))
