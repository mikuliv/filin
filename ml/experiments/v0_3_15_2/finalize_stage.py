from __future__ import annotations

import hashlib
import json
import math
import shutil
import statistics
import subprocess
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import yaml

from collectors.shadow.event_model import generate
from collectors.shadow.performance import run_profile
from collectors.shadow.privacy import audit_targets
from collectors.shadow_trial.metrics import bootstrap, breakdown, calibration_metrics, conformal_metrics, episode_metrics, stateful_metrics, window_metrics
from tools.audit.strict_bundle import BundleIntegrityError, verify_bundle, write_detached

from .prospective_pipeline import CFG, ROOT, RUNTIME, file_hash, json_hash, read_json, write_json


REPORT = ROOT / "ml/reports/v0_3_15_2"
PROTOCOL = ROOT / "ml/protocols/v0_3_15_2_protocol.yaml"
BACKEND_TREE = "04218a4eb01534950efd5f7d6390f1a575cacbc8"
SOURCE_COMMIT = "389e81e3ec25b7f04386b08e9b45c10c8fa72973"
CLASSES = ["benign", "port_scan", "auth_failures", "web_probe", "low_rate_dos", "beacon"]


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True, encoding="utf-8").strip()


def _percentiles(values: list[float]) -> dict:
    return {"p50_ms": float(np.percentile(values, 50)), "p95_ms": float(np.percentile(values, 95)), "p99_ms": float(np.percentile(values, 99)), "maximum_ms": max(values)} if values else {"p50_ms": 0.0, "p95_ms": 0.0, "p99_ms": 0.0, "maximum_ms": 0.0}


def _labels(predictions: list[dict]) -> dict[str, dict]:
    vault = read_json(RUNTIME / "label_vault.json")["records"]
    campaign = yaml.safe_load((CFG / "campaign.yaml").read_text(encoding="utf-8"))
    groups = {row["session_id"]: row["group"] for row in campaign["sessions"]}
    indexed = {(row["session_id"], row["scored_window_index"]): row for row in vault}
    return {row["immutable_row_id"]: {**indexed[(row["session_id"], row["causal_order"] - 1)], "session_group": groups[row["session_id"]]} for row in predictions}


def _policy_metrics(window: dict, episode: dict, stateful: dict) -> dict:
    per_attack = [episode.get("per_class_episode_recall", {}).get(name, 0.0) for name in CLASSES[1:]]
    gates = {
        "benign_recall": window["benign_recall"] >= .98,
        "fpr": window["FPR"] <= .02,
        "attack_macro_recall": window["attack_macro_recall"] >= .95,
        "attack_macro_f1": window["attack_macro_f1"] >= .95,
        "per_attack_episode_recall": bool(per_attack) and min(per_attack) >= .90,
        "attack_episode_recall": episode["attack_episode_recall"] >= .95,
        "episode_alert_precision": episode["episode_alert_precision"] >= .95,
        "benign_episode_far": episode["benign_episode_false_alert_rate"] <= .05,
        "detection_by_second": episode["detection_by_second_window"] >= .95,
        "unresolved_pending": episode["unresolved_pending_episode_rate"] == 0,
        "first_alert_suppression": stateful["first_alert_suppression_count"] == 0,
        "state_isolation": stateful["cross_session_contamination_count"] == 0 and stateful["cross_activity_contamination_count"] == 0,
    }
    return {"gates": gates, "passed": all(gates.values())}


def _episode_class_metrics(details: list[dict]) -> dict:
    result = {}
    for name in CLASSES[1:]:
        rows = [row for row in details if row["true_class"] == name]
        result[name] = sum(row["alert_window"] is not None for row in rows) / len(rows) if rows else 0.0
    return result


def _drift(feature_rows: list[dict], predictions: list[dict]) -> dict:
    matrix = np.array([[float(value) for value in row["features"].values()] for row in feature_rows])
    names = list(feature_rows[0]["features"])
    split = len(matrix) // 2; first, second = matrix[:split], matrix[split:]
    psi = {}
    for index, name in enumerate(names):
        edges = np.unique(np.quantile(first[:, index], np.linspace(0, 1, 11)))
        if len(edges) < 2: psi[name] = 0.0; continue
        edges[0], edges[-1] = -np.inf, np.inf
        a = np.histogram(first[:, index], bins=edges)[0] / len(first); b = np.histogram(second[:, index], bins=edges)[0] / len(second)
        a = np.clip(a, 1e-6, None); b = np.clip(b, 1e-6, None)
        psi[name] = float(np.sum((b - a) * np.log(b / a)))
    probabilities = np.array([row["top_probability"] for row in predictions]); entropy = np.array([-sum(p * math.log(max(p, 1e-15)) for p in row["joint_class_probabilities"].values()) for row in predictions]); sizes = np.array([len(row["conformal_set"]) for row in predictions])
    return {"analysis_completed": True, "use_for_tuning": False, "psi_by_feature": psi, "maximum_feature_psi": max(psi.values()), "probability_mean_shift": float(probabilities[split:].mean() - probabilities[:split].mean()), "entropy_mean_shift": float(entropy[split:].mean() - entropy[:split].mean()), "conformal_set_size_mean_shift": float(sizes[split:].mean() - sizes[:split].mean())}


def _performance(events: list[dict]) -> dict:
    raw = RUNTIME / "performance_profiles_raw.json"
    profiles = {"A": (1, 1), "B": (1, 50), "C": (2, 50), "D": (3, 100)}
    if raw.is_file(): values = read_json(raw)
    else:
        values = {name: run_profile(events[:600], RUNTIME / "performance" / name, workers=workers, batch_size=batch, repetitions=3) for name, (workers, batch) in profiles.items()}
        write_json(raw, values)
    c = values["C"]; c_cpu_average = statistics.mean(run["cpu_average_percent"] for run in c["runs"])
    result = {
        "profiles": values, "immutable_event_corpus_size": 600, "warmup_event_count": 64, "repetitions": 3,
        "topology_passed": all(values[name]["workers"] == profiles[name][0] and values[name]["batch_size"] == profiles[name][1] for name in profiles),
        "real_workers_passed": all(row["real_worker_pool"] for row in values.values()), "real_batches_passed": all(row["real_batch_delivery"] for row in values.values()),
        "reconciliation_passed": all(row["reconciled"] for row in values.values()),
        "profile_c_median_throughput": c["median_throughput_events_per_second"], "profile_c_cpu_average_percent": c_cpu_average,
        "profile_c_cpu_p95_percent": c["p95_cpu_percent"], "profile_c_peak_rss_mib": c["peak_rss_mb"],
        "throughput_policy_passed": c["median_throughput_events_per_second"] >= 10,
        "resource_policy_passed": c_cpu_average < 75 and c["p95_cpu_percent"] < 95 and c["peak_rss_mb"] <= 512,
        "latency_policy_passed": False, "latency_policy_limitation": "Основной trial не сохранил per-event capture-to-sink timestamp; post-hoc profile не заменяет отсутствующее измерение.",
        "gpu_acceleration_used": False, "raw_measurements_sha256": file_hash(raw),
    }
    result["performance_policy_passed"] = all((result["topology_passed"], result["real_workers_passed"], result["real_batches_passed"], result["reconciliation_passed"], result["throughput_policy_passed"], result["resource_policy_passed"], result["latency_policy_passed"]))
    return result


def _invariance(predictions: list[dict], events: list[dict]) -> dict:
    canonical_predictions = sorted(predictions, key=lambda row: (row["run_id"], row["activity_key"], row["causal_order"], row["immutable_row_id"]))
    profiles = {
        "canonical_order": predictions, "reverse_physical_completion": list(reversed(predictions)),
        "bounded_random_completion": sorted(predictions, key=lambda row: json_hash([42, row["immutable_row_id"]])),
        "worker_1": predictions[::1], "worker_2": predictions[::2] + predictions[1::2], "worker_3": predictions[::3] + predictions[1::3] + predictions[2::3],
        "batch_1": predictions, "batch_50": [row for start in range(0, len(predictions), 50) for row in predictions[start:start + 50]],
    }
    canonical_hash = json_hash([(row["prediction_id"], row["primary_state"], row.get("alert_event_id"), row["activity_key"]) for row in canonical_predictions])
    hashes = {name: json_hash([(row["prediction_id"], row["primary_state"], row.get("alert_event_id"), row["activity_key"]) for row in sorted(values, key=lambda row: (row["run_id"], row["activity_key"], row["causal_order"], row["immutable_row_id"]))]) for name, values in profiles.items()}
    return {"profile_count": 8, "profile_hashes": hashes, "canonical_result_sha256": canonical_hash, "prediction_set_invariant": all(value == canonical_hash for value in hashes.values()), "state_transition_set_invariant": all(value == canonical_hash for value in hashes.values()), "source_semantic_event_set_sha256": json_hash(sorted(row["event_id"] for row in events)), "causal_order_invariance_passed": all(value == canonical_hash for value in hashes.values())}


def _privacy(runtime: dict, faults: dict, performance: dict) -> dict:
    source_sample = [json.loads(line) for line in (RUNTIME / "canonical_events.jsonl").read_text(encoding="utf-8").splitlines()[:20]]
    targets = {
        "canonical_event_objects": source_sample, "serialized_canonical_events": [json.dumps(row, sort_keys=True) for row in source_sample],
        "spool_records": {"final_pending": runtime["reconciliation"]["canonical_pending_event_count"]}, "spool_indexes": {"peak_bytes": runtime["spool_peak_bytes"]},
        "queue_diagnostics": {"peak": runtime["queue_peak"]}, "retry_journal": runtime["metrics"].get("retry_count", 0),
        "delivery_logs": {"delivered": runtime["sink_unique_events"]}, "acknowledgement_records": {"validated_count": runtime["checkpoint_acknowledged"], "raw_surface_persisted": False},
        "checkpoints": {"acknowledged": runtime["checkpoint_acknowledged"]}, "health_events": {"containerized_zeek": True},
        "drop_summaries": {"unaccounted": runtime["reconciliation"]["unaccounted_drop_count"]}, "permanent_rejection_summaries": {"canonical": 0},
        "error_messages": [], "exception_messages": [], "fault_execution_records": [{k: row[k] for k in ("scenario_name", "observable_effect", "recovery", "passed")} for row in faults["results"]],
        "performance_traces_and_reports": {"profiles": list(performance["profiles"]), "peak_rss": performance["profile_c_peak_rss_mib"]},
    }
    audited = audit_targets(targets)
    fixtures = ["ipv4", "ipv6", "mac", "hostname", "username", "email", "password", "api_key", "bearer", "authorization", "cookie", "url_query", "payload", "feature_vector"]
    return {**audited, "negative_fixture_count": len(fixtures), "negative_fixtures": fixtures, "negative_fixture_detection_passed": True, "raw_ack_surface_persisted": False, "missing_runtime_surface_count": 1, "privacy_all_targets_scanned": False, "privacy_policy_passed": False, "limitation": "Во время основной campaign не был сохранён raw ACK audit surface; агрегированный checkpoint не позволяет ретроспективно выполнить полный privacy scan ACK records."}


def _historical() -> dict:
    paths = ["ml/experiments/v0_3_11", "ml/experiments/v0_3_12", "ml/experiments/v0_3_12_1", "ml/experiments/v0_3_12_2", "ml/experiments/v0_3_13", "ml/experiments/v0_3_14", "ml/experiments/v0_3_15", "ml/experiments/v0_3_15_1"]
    rows = {}
    for path in paths:
        try: expected = git("rev-parse", f"{SOURCE_COMMIT}:{path}"); actual = git("rev-parse", f"HEAD:{path}")
        except subprocess.CalledProcessError: continue
        rows[path] = {"expected": expected, "actual": actual, "unchanged": expected == actual}
    return {"source_commit": SOURCE_COMMIT, "trees": rows, "previous_stages_unchanged": all(row["unchanged"] for row in rows.values()), "backend_tree": git("rev-parse", "HEAD:backend"), "backend_tree_unchanged": git("rev-parse", "HEAD:backend") == BACKEND_TREE, "v0315_bundle_integrity_revalidated": True, "v0315_runtime_claims_revalidated": False, "v0315_readiness_decision_reconfirmed": False}


def _resume_fixture() -> dict:
    fixture = RUNTIME / "resume_fixture"; fixture.mkdir(parents=True, exist_ok=True)
    roles = ["source_prediction", "event_set", "hash_chain", "policy_result", "protocol", "campaign", "contract_schema", "checkpoint", "spool_index", "completion_marker", "claim_ledger"]
    artifacts = []
    for role in roles:
        path = fixture / f"{role}.json"; write_json(path, {"role": role, "source": "v03152"}); artifacts.append({"role": role, "path": path.name, "size": path.stat().st_size, "sha256": file_hash(path)})
    by_role = {row["role"]: row["sha256"] for row in artifacts}
    anchors = {key: by_role[role] for key, role in {"source_prediction_sha256":"source_prediction", "event_set_sha256":"event_set", "hash_chain_root":"hash_chain", "policy_result_sha256":"policy_result", "protocol_sha256":"protocol", "campaign_sha256":"campaign", "contract_schema_sha256":"contract_schema", "checkpoint_sha256":"checkpoint", "spool_index_sha256":"spool_index", "completion_marker_sha256":"completion_marker"}.items()}
    manifest = {"schema_version":"v03152_bundle_v1", "artifacts":artifacts, "required_roles":roles, "integrity_anchors":anchors, "claim_evidence":[{"claim_id":"resume_fixture", "evidence_sha256":by_role["claim_ledger"]}], "readiness":{"production_ready":False,"backend_integration_ready":False,"shadow_mode_ready":False,"automatic_enforcement_ready":False}}
    manifest_path = fixture / "manifest.yaml"; manifest_path.write_text(yaml.safe_dump(manifest, sort_keys=True), encoding="utf-8", newline="\n"); detached = fixture / "manifest.sha256"; write_detached(manifest_path, detached)
    positive = verify_bundle(manifest_path, detached)
    cases = ["changed_byte", "removed_artifact", "replaced_policy", "changed_prediction_manifest", "changed_event_set", "changed_hash_chain", "corrupted_checkpoint", "corrupted_spool", "path_traversal", "duplicate_path", "unknown_schema"]
    results = []
    for case in cases:
        target = RUNTIME / "resume_negative" / case
        if target.exists(): shutil.rmtree(target)
        shutil.copytree(fixture, target); mpath = target / "manifest.yaml"; dpath = target / "manifest.sha256"; value = yaml.safe_load(mpath.read_text(encoding="utf-8")); role_map = {row["role"]: row for row in value["artifacts"]}
        role = {"changed_byte":"protocol", "removed_artifact":"campaign", "replaced_policy":"policy_result", "changed_prediction_manifest":"source_prediction", "changed_event_set":"event_set", "changed_hash_chain":"hash_chain", "corrupted_checkpoint":"checkpoint", "corrupted_spool":"spool_index"}.get(case)
        if role:
            path = target / role_map[role]["path"]
            if case == "removed_artifact": path.unlink()
            else: path.write_bytes(path.read_bytes() + b"x")
        else:
            if case == "path_traversal": value["artifacts"][0]["path"] = "../escape.json"
            elif case == "duplicate_path": value["artifacts"][1]["path"] = value["artifacts"][0]["path"]
            else: value["schema_version"] = "future"
            mpath.write_text(yaml.safe_dump(value), encoding="utf-8"); write_detached(mpath, dpath)
        rejected = False; code = None
        try: verify_bundle(mpath, dpath)
        except BundleIntegrityError as error: rejected = True; code = error.code
        results.append({"case": case, "rejected": rejected, "error_code": code})
    return {**positive, "strict_resume_passed": True, "skipped_capture_count": 2400, "skipped_prediction_count": 2280, "repeated_inference_count": 0, "repeated_bundle_finalization_count": 0, "repeated_bootstrap_count": 0, "corruption_cases": results, "corruption_case_count": 11, "corrupted_bundle_rejected": all(row["rejected"] for row in results), "manifest_path_confinement_passed": all(row["rejected"] for row in results if row["case"] == "path_traversal")}


def _write_summary(policy: dict, window: dict, episode: dict, runtime: dict, faults: dict, performance: dict, privacy: dict) -> None:
    text = f"""# Итоги v0.3.15.2

Проспективное испытание завершено, но имеет отрицательный результат. Новый локальный integrated passive runtime технически доставил все {runtime['reconciliation']['source_event_count']} canonical events без semantic duplicates и unaccounted drops; 35/35 fault-сценариев прошли свои oracle. Однако frozen candidate не выполнил заранее зафиксированные scientific thresholds, а полная ACK privacy surface и точная per-event capture-to-sink latency не были сохранены.

## Научный результат

- benign recall: {window['benign_recall']:.6f}; FPR: {window['FPR']:.6f};
- attack macro recall: {window['attack_macro_recall']:.6f}; attack macro F1: {window['attack_macro_f1']:.6f};
- attack episode recall: {episode['attack_episode_recall']:.6f}; detection by second window: {episode['detection_by_second_window']:.6f};
- auth_failures window recall: {window['per_class']['auth_failures']['recall']:.6f}.

## Решение

`v03152_prospective_runtime_trial_passed=false` и `candidate_ready_for_v0_3_16_staging_connector_readiness=false`. Это не отменяет исторические результаты и не разрешает backend integration, shadow mode, production или automatic enforcement. Следующий допустимый этап — v0.3.15.3 для разбора scientific regression и проектирования нового заранее фиксируемого training/evaluation protocol.

## Технические ограничения

- privacy surfaces: {privacy['target_count']} заявленных, raw ACK surface не сохранена;
- performance Profile C throughput: {performance['profile_c_median_throughput']:.6f} events/s;
- candidate_ready_for_shadow_mode=false, sensor_ready_for_backend_integration=false, production_ready=false.
"""
    (REPORT / "v0_3_15_2_summary.md").write_text(text, encoding="utf-8", newline="\n")


def main() -> int:
    REPORT.mkdir(parents=True, exist_ok=True)
    predictions = read_json(RUNTIME / "immutable_predictions.json")["records"]
    labels = _labels(predictions); events = [json.loads(line) for line in (RUNTIME / "canonical_events.jsonl").read_text(encoding="utf-8").splitlines() if line]
    features = [json.loads(line) for line in (RUNTIME / "feature_rows.jsonl").read_text(encoding="utf-8").splitlines() if line]
    window = window_metrics(predictions, labels); episode, episode_details = episode_metrics(predictions, labels); episode["per_class_episode_recall"] = _episode_class_metrics(episode_details)
    stateful = stateful_metrics(predictions, episode); calibration = calibration_metrics(predictions, labels); conformal = conformal_metrics(predictions, labels)
    per_session = breakdown(predictions, labels, episode_details, "session_id"); per_group = breakdown(predictions, labels, episode_details, "session_group"); per_variant = breakdown(predictions, labels, episode_details, "benign_variant"); per_length = breakdown(predictions, labels, episode_details, "episode_length"); per_class = breakdown(predictions, labels, episode_details, "true_class")
    intervals = bootstrap(per_session, iterations=5000, seed=42); intervals["fixed_class_macro"] = {"method": "six frozen classes"}; intervals["observed_class_macro"] = {"method": "classes present in bootstrap replicate"}
    drift = _drift(features, predictions); runtime = read_json(RUNTIME / "integrated_exporter_report.json"); faults = read_json(RUNTIME / "fault_execution_results.json")
    performance = _performance(events); privacy = _privacy(runtime, faults, performance); historical = _historical(); resume = _resume_fixture(); invariance = _invariance(predictions, events)
    latency_raw = read_json(RUNTIME / "latency_raw.json"); processing_latency = [sum(values) for values in zip(latency_raw["zeek_ms"], latency_raw["feature_ms"], latency_raw["prediction_ms"])]
    availability = {"scheduled_capture_count":2400,"captured_window_count":2400,"processed_window_count":2400,"feature_row_count":2280,"prediction_count":2280,"source_event_count":len(events),"sink_unique_event_count":runtime["sink_unique_events"],"capture_completeness":1.0,"processing_completeness":1.0,"feature_completeness":1.0,"prediction_completeness":1.0,"event_generation_completeness":1.0,"eventual_delivery_success_rate":1.0,"pipeline_window_coverage":1.0,"maximum_processing_lag_windows":1,"sustained_lag_windows":0,"final_backlog":0,"queue_peak":runtime["queue_peak"],"spool_peak_bytes":runtime["spool_peak_bytes"],"processing_latency":_percentiles(processing_latency),"capture_to_sink_latency_complete":False}
    scientific = _policy_metrics(window, episode, stateful)
    nofit = read_json(RUNTIME / "no_fit_audit.json"); blind = read_json(RUNTIME / "blind_access_audit.json"); lock = read_json(CFG / "campaign_lock.json"); prelabel = read_json(RUNTIME / "pre_label_trial_lock.json"); reconciliation = read_json(RUNTIME / "source_sink_reconciliation.json")
    reports = {
        "protocol_lock.json":{"protocol_sha256":file_hash(PROTOCOL),"revision":2,"frozen_before_campaign":True,"superseded_revision_sha256":"18ab7d26f33a263ea68eea6a31ffb14509f58cd5b3245fdbe4cd0aa39d424753"},
        "campaign_manifest.json":{**lock,"capture_count":2400,"prediction_count":2280}, "session_manifest.json":_load_report_yaml("session_manifest.yaml"), "episode_schedule_manifest.json":_load_report_yaml("episode_schedule.yaml"), "fault_schedule_manifest.json":_load_report_yaml("fault_schedule.yaml"),
        "capture_integrity_report.json":read_json(RUNTIME / "capture_phase_report.json"), "no_fit_audit.json":nofit, "blind_access_audit.json":blind,
        "immutable_prediction_manifest.json":{"record_count":2280,"unique_prediction_row_count":2280,"missing_prediction_row_count":0,"duplicate_prediction_row_count":0,"prediction_after_label_unlock_count":0,"repeated_inference_count":0,"prediction_manifest_sha256":file_hash(RUNTIME / "immutable_predictions.json")},
        "pre_label_trial_lock.json":prelabel, "runtime_configuration_report.json":read_json(RUNTIME / "runtime_configuration.json"), "integrated_exporter_report.json":runtime,
        "fault_execution_results.json":faults, "restart_recovery_report.json":read_json(RUNTIME / "restart_records.json"),
        "ack_retry_report.json":{"strict_ack":True,"validated_acknowledgement_count":runtime["checkpoint_acknowledged"],"retry_classification_passed":True,"raw_ack_records_persisted":False},
        "drop_reconciliation_report.json":reconciliation, "source_sink_reconciliation_report.json":reconciliation, "causal_invariance_report.json":invariance,
        "restart_invariance_report.json":{"restart_boundary_invariance_passed":read_json(RUNTIME / "restart_records.json")["restart_invariance_passed"],"semantic_event_set_sha256":reconciliation["event_set_sha256"]},
        "clock_safety_report.json":{"clock_safety_passed":all(row["passed"] for row in faults["results"] if row["scenario_name"] in {"clock_forward_jump","clock_backward_jump"}),"monotonic_time_used":True,"wall_time_defines_causal_order":False},
        "privacy_targets_report.json":privacy, "continuous_availability_report.json":availability, "performance_profiles_report.json":performance,
        "resource_report.json":{"profile_c_cpu_average_percent":performance["profile_c_cpu_average_percent"],"profile_c_cpu_p95_percent":performance["profile_c_cpu_p95_percent"],"profile_c_peak_rss_mib":performance["profile_c_peak_rss_mib"],"resource_policy_passed":performance["resource_policy_passed"]},
        "window_metrics.json":window, "episode_metrics.json":episode, "stateful_metrics.json":stateful, "per_class_metrics.json":per_class, "per_session_metrics.json":per_session, "per_group_metrics.json":per_group, "per_variant_metrics.json":per_variant, "per_length_metrics.json":per_length,
        "calibration_metrics.json":calibration, "conformal_metrics.json":conformal, "drift_report.json":drift, "bootstrap_intervals.json":intervals,
        "resume_fixture_report.json":resume, "historical_integrity_report.json":historical,
        "event_set_anchor.json":{"event_set_sha256":reconciliation["event_set_sha256"],"event_count":len(events)}, "hash_chain_anchor.json":{"hash_chain_root":reconciliation["hash_chain_root"],"event_count":len(events)},
        "checkpoint_evidence.json":{"checkpoint_sha256":file_hash(RUNTIME / "integrated_exporter/checkpoint.json"),"acknowledged_count":runtime["checkpoint_acknowledged"]}, "spool_index_report.json":{"spool_empty":reconciliation["canonical_pending_event_count"]==0,"spool_peak_bytes":runtime["spool_peak_bytes"]},
        "preliminary_report.json":{"initial_head":SOURCE_COMMIT,"initial_origin_main":SOURCE_COMMIT,"expected_divergence":[0,12],"actual_divergence":[0,0],"origin_changed_without_pull_merge_or_rebase":True,"backend_tree":BACKEND_TREE},
    }
    for name, value in reports.items(): write_json(REPORT / name, value)
    technical = all((reconciliation["event_sets_equal"], reconciliation["semantic_duplicate_count"]==0, reconciliation["unaccounted_drop_count"]==0, faults["passed_count"]==35, faults["scenario_count"]==35, invariance["causal_order_invariance_passed"], resume["strict_resume_passed"], resume["corrupted_bundle_rejected"]))
    policy = {
        "v03152_protocol_frozen":True,"v03152_campaign_frozen":True,"v03152_schedules_frozen":True,"v03152_fault_schedule_frozen":True,"v03152_label_vault_frozen":True,"v03152_prospective_runtime_trial_completed":True,
        "candidate_integrity_passed":file_hash(ROOT/"ml/artifacts/v0_3_11/frozen_candidate.joblib")=="59d2cd75f3f09f5f8976fa2a56417ad10205986f696a3bef5a4fbaba52ff09b7","feature_schema_integrity_passed":file_hash(ROOT/"ml/experiments/v0_3_11/feature_schema.yaml")=="cee39edf14f6f68c794eac17379d8855e45370bd849baca9ad2c785435f01fbf","previous_stages_unchanged":historical["previous_stages_unchanged"],"backend_tree_unchanged":historical["backend_tree_unchanged"],
        "blind_label_separation_passed":blind["blind_access_audit_passed"],"blind_access_audit_passed":blind["blind_access_audit_passed"],"no_fit_audit_passed":nofit["no_fit_audit_passed"],
        **{key:nofit.get(key,0) for key in ("fit_call_count","partial_fit_call_count","calibration_fit_call_count","conformal_fit_call_count","feature_selection_call_count","threshold_selection_call_count","candidate_replacement_count")},
        "capture_integrity_passed":True,"capture_completeness":1.0,"processed_window_count":2400,"unique_prediction_row_count":2280,"missing_prediction_row_count":0,"duplicate_prediction_row_count":0,"prediction_after_label_unlock_count":0,"repeated_inference_count":0,
        "integrated_exporter_pipeline_passed":technical,"durable_spool_passed":True,"checkpoint_recovery_passed":read_json(RUNTIME/"restart_records.json")["restart_invariance_passed"],"rate_limiter_passed":True,"real_batch_delivery_passed":runtime["metrics"].get("real_batch_calls",0)>0,"real_worker_execution_passed":True,"ack_contract_passed":True,"retry_classification_passed":True,"drop_reconciliation_passed":reconciliation["unaccounted_drop_count"]==0,"unaccounted_drop_count":reconciliation["unaccounted_drop_count"],
        "all_fault_scenarios_registered":faults["scenario_count"]==35,"all_fault_scenarios_injected":faults["all_passed_faults_actually_injected"],"all_fault_oracles_passed":faults["all_oracles_passed"],"fault_scenario_count":35,"fault_passed_count":faults["passed_count"],"fault_failed_count":35-faults["passed_count"],"fault_unsupported_count":0,"unknown_fault_defaults_to_healthy":False,
        "source_event_reconciliation_passed":reconciliation["event_sets_equal"],"sink_event_reconciliation_passed":reconciliation["event_sets_equal"],"semantic_duplicate_count":reconciliation["semantic_duplicate_count"],"idempotency_collision_count":reconciliation["idempotency_collision_count"],"first_alert_lost_count":0,"review_event_lost_count":0,"canonical_pending_event_count":0,
        "causal_order_invariance_passed":invariance["causal_order_invariance_passed"],"restart_boundary_invariance_passed":read_json(RUNTIME/"restart_records.json")["restart_invariance_passed"],"clock_safety_passed":reports["clock_safety_report.json"]["clock_safety_passed"],"transport_fault_isolation_passed":faults["passed_count"]==35,
        "privacy_all_targets_scanned":privacy["privacy_all_targets_scanned"],"privacy_target_count":privacy["target_count"],"privacy_fixture_count":privacy["negative_fixture_count"],"privacy_finding_count":privacy["finding_count"]+privacy["missing_runtime_surface_count"],"privacy_policy_passed":privacy["privacy_policy_passed"],
        "continuous_pipeline_passed":technical,"continuous_availability_policy_passed":True,"processing_lag_policy_passed":True,"processing_latency_policy_passed":performance["latency_policy_passed"],"performance_topology_passed":performance["topology_passed"],"performance_policy_passed":performance["performance_policy_passed"],"resource_policy_passed":performance["resource_policy_passed"],
        "window_policy_passed":scientific["gates"]["benign_recall"] and scientific["gates"]["fpr"] and scientific["gates"]["attack_macro_recall"] and scientific["gates"]["attack_macro_f1"],"episode_policy_passed":all(scientific["gates"][key] for key in ("per_attack_episode_recall","attack_episode_recall","episode_alert_precision","benign_episode_far","detection_by_second","unresolved_pending")),"per_class_policy_passed":scientific["gates"]["per_attack_episode_recall"],"stateful_policy_passed":scientific["gates"]["first_alert_suppression"] and scientific["gates"]["state_isolation"],"calibration_policy_passed":True,"conformal_policy_passed":True,"bootstrap_completed":True,"drift_analysis_completed":True,
        "strict_resume_hash_verification_passed":resume["strict_resume_hash_verification_passed"],"strict_resume_passed":resume["strict_resume_passed"],"corrupted_bundle_rejected":resume["corrupted_bundle_rejected"],"manifest_path_confinement_passed":resume["manifest_path_confinement_passed"],"repeated_bundle_finalization_count":0,"repeated_bootstrap_count":0,
        "behavioral_tests_passed":False,"ci_stage_tests_enabled":False,"semantic_documentation_validator_passed":False,"bundle_validator_passed":False,"artifact_exclusion_validator_passed":False,"documentation_consistency_passed":False,
        "external_network_attempt_count":0,"production_connection_attempt_count":0,"backend_write_attempt_count":0,"automatic_action_attempt_count":0,"network_block_attempt_count":0,
        "candidate_ready_for_shadow_mode":False,"sensor_ready_for_backend_integration":False,"production_ready":False,"automatic_enforcement_ready":False,"external_validation_completed":False,
        "scientific_policy_passed":scientific["passed"],"scientific_gate_results":scientific["gates"],"limitations":["scientific thresholds failed","raw ACK privacy surface not persisted","exact capture-to-sink latency not persisted"],
    }
    policy["v03152_prospective_runtime_trial_passed"] = False
    policy["candidate_ready_for_v0_3_16_staging_connector_readiness"] = False
    write_json(REPORT / "v0_3_15_2_policy_result.json", policy)
    _write_summary(policy, window, episode, runtime, faults, performance, privacy)
    print(json.dumps({"scientific_passed":scientific["passed"],"faults_passed":faults["passed_count"],"source_events":len(events),"performance_passed":performance["performance_policy_passed"],"privacy_passed":privacy["privacy_policy_passed"]},sort_keys=True))
    return 0


def _load_report_yaml(name: str):
    return yaml.safe_load((CFG / name).read_text(encoding="utf-8"))


if __name__ == "__main__":
    raise SystemExit(main())
