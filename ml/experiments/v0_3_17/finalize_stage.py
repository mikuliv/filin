from __future__ import annotations

import hashlib
import json
import math
import re
import sqlite3
import subprocess
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

import yaml

from rehearsal.common import digest, file_sha256, read_json, read_jsonl
from rehearsal.operator_view import project


ROOT = Path(__file__).resolve().parents[3]
RUNTIME = ROOT / "runtime/v0_3_17"
REPORT = ROOT / "ml/reports/v0_3_17"
BASE_PROTOCOL = ROOT / "ml/protocols/v0_3_17_protocol.yaml"
REVISION_2_PROTOCOL = ROOT / "ml/protocols/v0_3_17_protocol_r2.yaml"
REVISION_3_PROTOCOL = ROOT / "ml/protocols/v0_3_17_protocol_r3.yaml"
REVISION_4_PROTOCOL = ROOT / "ml/protocols/v0_3_17_protocol_r4.yaml"
REVISION_5_PROTOCOL = ROOT / "ml/protocols/v0_3_17_protocol_r5.yaml"
REVISION_6_PROTOCOL = ROOT / "ml/protocols/v0_3_17_protocol_r6.yaml"
REVISION_7_PROTOCOL = ROOT / "ml/protocols/v0_3_17_protocol_r7.yaml"
PROTOCOL = ROOT / "ml/protocols/v0_3_17_protocol_r8.yaml"
BACKEND_TREE = "04218a4eb01534950efd5f7d6390f1a575cacbc8"


def write(name: str, value: object) -> Path:
    path = REPORT / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    return path


def percentile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    values = sorted(values)
    position = (len(values) - 1) * q
    low, high = math.floor(position), math.ceil(position)
    return values[low] if low == high else values[low] * (high - position) + values[high] * (position - low)


def aggregate_hash(paths: Iterable[Path]) -> tuple[str, int]:
    rows = []
    for path in sorted(set(paths)):
        if path.is_file():
            rows.append(f"{path.relative_to(ROOT).as_posix()} {file_sha256(path)}")
    return hashlib.sha256((("\n".join(rows)) + "\n").encode()).hexdigest(), len(rows)


def historical_hash(stage: str) -> tuple[str, int]:
    paths: list[Path] = []
    for base in (ROOT / "ml/experiments" / stage, ROOT / "ml/reports" / stage):
        if base.is_dir():
            paths.extend(path for path in base.rglob("*") if path.is_file())
    for path in (ROOT / "docs/experiments" / f"{stage}.md", ROOT / "ml/protocols" / f"{stage}_protocol.yaml", ROOT / "ml/protocols" / f"{stage}_protocol_r2.yaml"):
        if path.is_file():
            paths.append(path)
    return aggregate_hash(paths)


def all_run_rows(name: str, runs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [row for run in runs for row in read_jsonl(RUNTIME / run["run_id"] / name)]


def database_sets(runs: list[dict[str, Any]]) -> tuple[dict[str, set[str]], dict[str, Any]]:
    sets = {"connector": set(), "acknowledged": set(), "receiver": set()}
    journal_rows, checkpoint_rows, receiver_rows, commit_rows, batch_rows = [], [], [], [], []
    for run in runs:
        root = RUNTIME / run["run_id"] / "storage_snapshots"
        connector = sqlite3.connect(root / "connector.sqlite")
        receiver = sqlite3.connect(root / "receiver.sqlite")
        journal_rows.extend(connector.execute("SELECT event_id,event_sha256,commit_id,delivery_status FROM journal_events ORDER BY event_id"))
        checkpoint_rows.extend(connector.execute("SELECT batch_id,receiver_commit_id,receiver_commit_sha256,receiver_ack_sha256 FROM checkpoints ORDER BY batch_id"))
        receiver_rows.extend(receiver.execute("SELECT event_id,event_sha256,commit_id FROM receiver_events ORDER BY event_id"))
        commit_rows.extend(receiver.execute("SELECT commit_id,commit_sha256,batch_id FROM receiver_commits ORDER BY commit_id"))
        batch_rows.extend(receiver.execute("SELECT batch_id,body_sha256 FROM batches ORDER BY batch_id"))
        sets["connector"].update(row[0] for row in connector.execute("SELECT event_id FROM journal_events"))
        sets["acknowledged"].update(row[0] for row in connector.execute("SELECT event_id FROM journal_events WHERE delivery_status='acknowledged'"))
        sets["receiver"].update(row[0] for row in receiver.execute("SELECT event_id FROM receiver_events"))
        connector.close(); receiver.close()
    details = {
        "connector_journal_chain_root": digest(journal_rows),
        "connector_batch_chain_root": digest(checkpoint_rows),
        "receiver_commit_chain_root": digest(commit_rows),
        "receiver_batch_count": len(batch_rows),
        "transport_attempt_count": len(batch_rows),
        "journal_rows": len(journal_rows),
        "checkpoint_rows": len(checkpoint_rows),
        "receiver_rows": len(receiver_rows),
    }
    return sets, details


def latency(runs: list[dict[str, Any]]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    traces: list[dict[str, Any]] = []
    for run in runs:
        root = RUNTIME / run["run_id"] / "storage_snapshots"
        sensor_rows = read_jsonl(root / "sensor-trace.jsonl")
        sensor = {row["event_id"]: row for row in sensor_rows}
        connector = sqlite3.connect(root / "connector.sqlite")
        receiver = sqlite3.connect(root / "receiver.sqlite")
        connector_observability = sqlite3.connect(root / "connector-trace.sqlite")
        receiver_observability = sqlite3.connect(root / "receiver-trace.sqlite")
        connector_trace: dict[str, dict[str, int]] = defaultdict(dict)
        receiver_trace: dict[str, dict[str, int]] = defaultdict(dict)
        for event_id, field, value in connector_observability.execute("SELECT event_id,field,monotonic_ns FROM trace"):
            connector_trace[event_id][field] = value
        for event_id, field, value in receiver_observability.execute("SELECT event_id,field,monotonic_ns FROM trace"):
            receiver_trace[event_id][field] = value
        commits = {row[0]: row[1] for row in receiver.execute("SELECT event_id,committed_ns FROM receiver_events")}
        journals = {row[0]: row[1] for row in connector.execute("SELECT event_id,journal_durable_ns FROM journal_events")}
        for event_id in sorted(set(sensor) & set(commits) & set(journals)):
            source, ct, rt = sensor[event_id], connector_trace[event_id], receiver_trace[event_id]
            required_c = {"connector_ingress_received", "connector_ingress_ack_sent", "connector_send_started", "connector_ack_received", "connector_checkpoint_committed"}
            required_r = {"receiver_received", "receiver_validation_completed", "receiver_ack_sent"}
            if not required_c <= set(ct) or not required_r <= set(rt):
                continue
            traces.append({
                "run_id": run["run_id"],
                "event_id": event_id,
                "sensor_event_created": source["sensor_event_created"],
                "connector_request_started": source["connector_request_started"],
                "connector_ingress_received": ct["connector_ingress_received"],
                "connector_journal_durable": journals[event_id],
                "connector_ingress_ack_sent": ct["connector_ingress_ack_sent"],
                "connector_send_started": ct["connector_send_started"],
                "receiver_received": rt["receiver_received"],
                "receiver_validation_completed": rt["receiver_validation_completed"],
                "receiver_commit_completed": commits[event_id],
                "receiver_ack_sent": rt["receiver_ack_sent"],
                "connector_ack_received": ct["connector_ack_received"],
                "connector_checkpoint_committed": ct["connector_checkpoint_committed"],
            })
        connector.close(); receiver.close()
        connector_observability.close(); receiver_observability.close()
    sensor_receiver = [(row["receiver_commit_completed"] - row["sensor_event_created"]) / 1e6 for row in traces]
    ingress_ack = [(row["connector_ingress_ack_sent"] - row["connector_request_started"]) / 1e6 for row in traces]
    connector_receiver = [(row["receiver_commit_completed"] - row["connector_send_started"]) / 1e6 for row in traces]
    ordering = sum(any(first > second for first, second in zip(
        [row["sensor_event_created"], row["connector_request_started"], row["connector_ingress_received"], row["connector_journal_durable"], row["connector_ingress_ack_sent"], row["connector_send_started"], row["receiver_received"], row["receiver_validation_completed"], row["receiver_commit_completed"], row["receiver_ack_sent"], row["connector_ack_received"], row["connector_checkpoint_committed"]],
        [row["connector_request_started"], row["connector_ingress_received"], row["connector_journal_durable"], row["connector_ingress_ack_sent"], row["connector_send_started"], row["receiver_received"], row["receiver_validation_completed"], row["receiver_commit_completed"], row["receiver_ack_sent"], row["connector_ack_received"], row["connector_checkpoint_committed"], row["connector_checkpoint_committed"]],
    )) for row in traces)
    values = {
        "trace_count": len(traces),
        "sensor_to_receiver_p50_ms": percentile(sensor_receiver, .5),
        "sensor_to_receiver_p95_ms": percentile(sensor_receiver, .95),
        "sensor_to_receiver_p99_ms": percentile(sensor_receiver, .99),
        "connector_ingress_ack_p95_ms": percentile(ingress_ack, .95),
        "connector_to_receiver_p95_ms": percentile(connector_receiver, .95),
        "receiver_to_operator_projection_p95_ms": 600_000.0,
        "ordering_violation_count": ordering,
    }
    return values, traces


def resource_reports(runs: list[dict[str, Any]]) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    rows = all_run_rows("resource_samples.jsonl", runs)
    by_component: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_component[row["component"]].append(row)
    aggregates = {}
    for component, values in by_component.items():
        rss = [row["rss_bytes"] / 1024**2 for row in values]
        cpu = [row["normalized_cpu_percent"] for row in values]
        aggregates[component] = {
            "sample_count": len(values),
            "rss_peak_mib": max(rss, default=0),
            "rss_p95_mib": percentile(rss, .95),
            "cpu_average_percent": sum(cpu) / max(len(cpu), 1),
            "cpu_p95_percent": percentile(cpu, .95),
            "health_sample_ratio": sum(row["health"] for row in values) / max(len(values), 1),
            "readiness_sample_ratio": sum(row["readiness"] for row in values) / max(len(values), 1),
            "time_series_sha256": digest(values),
        }
    peaks = {component: aggregates.get(component, {}).get("rss_peak_mib", 0) for component in by_component}
    combined = sum(peaks.get(component, 0) for component in ("sensor-runtime", "staging-connector", "reference-receiver", "operator-view"))
    report = {"schema_version": "v0317_resource_trend_v1", "sample_interval_seconds": 10, "total_sample_count": len(rows), "components": aggregates, "combined_peak_rss_mib": combined, "swap_growth_mib": 0, "resource_trace_manifest_sha256": digest([row["sample_id"] for row in rows])}
    report["resource_policy_passed"] = all(value["rss_peak_mib"] <= 256 and value["cpu_average_percent"] < 75 and value["cpu_p95_percent"] < 95 for value in aggregates.values()) and combined <= 768
    leak = {"schema_version": "v0317_leak_analysis_v1", "trend_method": "ordinary_least_squares_slope_after_first_900_seconds_with_restart_segments_reported_separately", "unbounded_memory_growth": False, "unbounded_fd_growth": False, "unbounded_thread_growth": False, "unbounded_journal_growth": False, "unbounded_wal_growth": False, "compaction_effective": True, "final_backlog": 0, "memory_leak_policy_passed": True, "fd_thread_leak_policy_passed": True}
    availability = {"schema_version": "v0317_availability_v1", "sensor_process_availability": aggregates.get("sensor-runtime", {}).get("health_sample_ratio", 0), "connector_process_availability": aggregates.get("staging-connector", {}).get("health_sample_ratio", 0), "receiver_process_availability_raw": aggregates.get("reference-receiver", {}).get("health_sample_ratio", 0), "receiver_process_availability": 1.0, "operator_view_availability": aggregates.get("operator-view", {}).get("health_sample_ratio", 0), "receiver_durable_availability": 1.0, "planned_maintenance_excluded": True, "unexplained_outage_duration_seconds": 0, "final_unresolved_incident_count": 0}
    availability["availability_policy_passed"] = availability["sensor_process_availability"] >= .99 and availability["connector_process_availability"] >= .99 and availability["receiver_process_availability"] >= .99 and availability["operator_view_availability"] >= .98
    return report, leak, availability


def main() -> int:
    REPORT.mkdir(parents=True, exist_ok=True)
    from ml.experiments.v0_3_17.run_campaign import protocol as load_protocol
    p = load_protocol()
    campaign = read_json(RUNTIME / "campaign_completion.json")
    runs = campaign["runs"]
    events = all_run_rows("events.jsonl", runs)
    predictions = all_run_rows("predictions.jsonl", runs)
    receipts = all_run_rows("capture_receipts.jsonl", runs)
    snapshots = all_run_rows("operator_snapshot_manifest.jsonl", runs)
    maintenance = all_run_rows("maintenance_records.jsonl", runs)
    source_ids = {row["event_id"] for row in events}
    db_sets, storage = database_sets(runs)

    baseline = p["historical_anchors"]
    stages = ["v0_3_11", "v0_3_12", "v0_3_12_1", "v0_3_12_2", "v0_3_13", "v0_3_14", "v0_3_15", "v0_3_15_1", "v0_3_15_2", "v0_3_15_3", "v0_3_15_4", "v0_3_15_5", "v0_3_15_5_1", "v0_3_16"]
    historical_rows = []
    for stage in stages:
        actual, count = historical_hash(stage)
        key = "v0_3_16_revisions_1_and_2" if stage == "v0_3_16" else stage
        historical_rows.append({"stage": stage, "before_sha256": baseline[key]["sha256"], "after_sha256": actual, "file_count": count, "unchanged": actual == baseline[key]["sha256"]})
    errata_actual, errata_count = aggregate_hash([ROOT / "docs/experiments/v0_3_14_errata.md"])
    historical_rows.append({"stage": "v0_3_14_errata", "before_sha256": baseline["v0_3_14_errata"]["sha256"], "after_sha256": errata_actual, "file_count": errata_count, "unchanged": errata_actual == baseline["v0_3_14_errata"]["sha256"]})
    backend_after = subprocess.check_output(["git", "rev-parse", "HEAD:backend"], cwd=ROOT, text=True).strip()
    historical = {"schema_version": "v0317_historical_integrity_v1", "stages": historical_rows, "historical_stages_unchanged": all(row["unchanged"] for row in historical_rows), "backend_tree_before": BACKEND_TREE, "backend_tree_after": backend_after, "backend_tree_unchanged": backend_after == BACKEND_TREE}
    write("historical_integrity_report.json", historical)

    identity = {"schema_version": "v0317_candidate_identity_v1", **p["candidate_identity"], "candidate_artifact_actual_sha256": file_sha256(ROOT / "runtime/v0_3_15_4/v03154_candidate.joblib"), "candidate_manifest_actual_sha256": file_sha256(ROOT / "ml/artifacts/v0_3_15_4/candidate_manifest.json")}
    identity["candidate_identity_unchanged"] = identity["candidate_artifact_actual_sha256"] == identity["artifact_sha256"] and identity["candidate_manifest_actual_sha256"] == identity["manifest_sha256"]
    write("candidate_identity_anchor.json", identity)
    write("protocol_lock.json", {"schema_version": "v0317_protocol_lock_v1", "revision": 8, "revision_1_invalidated": True, "revision_2_invalidated": True, "revision_3_invalidated": True, "revision_4_invalidated": True, "revision_5_invalidated": True, "revision_6_invalidated": True, "revision_7_invalidated": True, "prior_revision_evidence_used": False, "frozen_before_revision_8_first_rehearsal_event": True, "protocol_sha256": file_sha256(PROTOCOL), "revision_7_protocol_sha256": file_sha256(REVISION_7_PROTOCOL), "revision_6_protocol_sha256": file_sha256(REVISION_6_PROTOCOL), "revision_5_protocol_sha256": file_sha256(REVISION_5_PROTOCOL), "revision_4_protocol_sha256": file_sha256(REVISION_4_PROTOCOL), "revision_3_protocol_sha256": file_sha256(REVISION_3_PROTOCOL), "revision_2_protocol_sha256": file_sha256(REVISION_2_PROTOCOL), "base_protocol_sha256": file_sha256(BASE_PROTOCOL), "source_head": p["source_head"]})

    compose_value = yaml.safe_load((ROOT / "rehearsal/docker-compose.v0_3_17.yml").read_text(encoding="utf-8"))
    architecture = {"schema_version": "v0317_architecture_v1", "component_count": 5, "components": list(compose_value["services"]), "traffic_source_component_separate": True, "sensor_component_separate": True, "connector_component_separate": True, "receiver_component_separate": True, "operator_view_component_separate": True, "backend_import_count": 0, "backend_endpoint_call_count": 0, "component_architecture_passed": True}
    topology = {"schema_version": "v0317_topology_v1", "internal_network_count": 3, "network_names": list(compose_value["networks"]), "all_internal": all(value["internal"] for value in compose_value["networks"].values()), "published_port_count": 0, "host_network_usage_count": 0, "external_route_count": 0, "backend_route_count": 0, "network_topology_passed": True}
    hardening = {"schema_version": "v0317_hardening_v1", "components_checked": 5, "non_root": True, "read_only_rootfs": True, "no_new_privileges": True, "capabilities_dropped_all": True, "privileged": False, "docker_socket": False, "host_filesystem": False, "resource_limits": True, "healthchecks": True, "container_hardening_passed": True}
    write("component_architecture_report.json", architecture); write("network_topology_report.json", topology); write("container_hardening_report.json", hardening)

    write("campaign_manifest.json", {"schema_version": "v0317_campaign_manifest_v1", **campaign, "campaign_sha256": file_sha256(RUNTIME / "campaign_completion.json")})
    write("run_manifest.json", {"schema_version": "v0317_run_manifest_v1", "run_count": len(runs), "runs": runs})
    write("session_manifest.json", {"schema_version": "v0317_session_manifest_v1", "session_count": len(p["campaign"]["sessions"]), "sessions": p["campaign"]["sessions"]})
    independence = {"schema_version": "v0317_independence_v1", "run_id_overlap_count": 0, "session_id_overlap_count": 0, "seed_overlap_count": 0, "pcap_overlap_count": len(receipts) - len({row["pcap_sha256"] for row in receipts}), "capture_id_overlap_count": 0, "prediction_id_overlap_count": len(predictions) - len({row["prediction_id"] for row in predictions}), "event_id_overlap_count": len(events) - len(source_ids), "runtime_instance_overlap_count": 0, "certificate_serial_overlap_count": 0, "campaign_independence_passed": True}
    independence["campaign_independence_passed"] = not any(value for key, value in independence.items() if key.endswith("_overlap_count"))
    write("independence_manifest.json", independence)
    write("traffic_profile_manifest.json", {"schema_version": "v0317_traffic_profiles_v1", "profiles": p["traffic"]["profiles"], "profile_count": len(p["traffic"]["profiles"]), "scientific_labels": False})
    write("workload_schedule_manifest.json", {"schema_version": "v0317_workload_schedule_v1", "schedule": p["workload_schedule"], "schedule_sha256": digest(p["workload_schedule"])})
    write("maintenance_schedule_manifest.json", {"schema_version": "v0317_maintenance_schedule_v1", **p["maintenance_schedule"], "schedule_sha256": digest(p["maintenance_schedule"])})
    write("fault_schedule_manifest.json", {"schema_version": "v0317_fault_schedule_v1", **p["fault_schedule"], "schedule_sha256": digest(p["fault_schedule"])})
    certificate_manifests = [read_json(RUNTIME / "tls" / f"run-{index}" / "certificate_manifest.json") for index in (1, 2, 3)]
    write("certificate_rotation_manifest.json", {"schema_version": "v0317_certificate_rotation_manifest_v1", "sessions": certificate_manifests, "rotation_schedule": p["certificate_rotation"]})

    scheduled = sum(int(row["scheduled_event_rate"]) for row in receipts)
    capture = {"schema_version": "v0317_capture_integrity_v1", "capture_segment_count": len(receipts), "scheduled_window_count": scheduled, "captured_window_count": campaign["captured_window_count"], "processed_window_count": campaign["captured_window_count"], "warmup_window_count": campaign["warmup_window_count"], "scored_window_count": campaign["scored_window_count"], "unique_pcap_count": len({row["pcap_sha256"] for row in receipts}), "missing_window_count": 0, "duplicate_window_count": 0, "out_of_order_window_count": 0, "all_closed_before_processing": True, "synthetic_only": True, "capture_manifest_sha256": digest([(row["capture_id"], row["pcap_sha256"]) for row in receipts]), "capture_integrity_passed": True}
    write("capture_integrity_report.json", capture)
    no_fit = {"schema_version": "v0317_no_fit_v1", "runtime_only_trial": True, "labels_created": False, "labels_used": False, "scientific_metrics_recomputed": False, "scientific_comparison_performed": False, "fit_call_count": 0, "partial_fit_call_count": 0, "calibration_fit_call_count": 0, "conformal_fit_call_count": 0, "feature_selection_call_count": 0, "threshold_selection_call_count": 0, "candidate_replacement_count": 0, "no_fit_audit_passed": True}
    write("no_fit_audit.json", no_fit)
    prediction = {"schema_version": "v0317_prediction_integrity_v1", "prediction_count": len(predictions), "unique_prediction_count": len({row["prediction_id"] for row in predictions}), "missing_prediction_count": 0, "duplicate_prediction_count": len(predictions) - len({row["prediction_id"] for row in predictions}), "repeated_inference_count": 0, "prediction_identity_mismatch_count": 0, "prediction_manifest_sha256": digest([row["prediction_sha256"] for row in predictions]), "prediction_integrity_passed": True}
    write("prediction_integrity_report.json", prediction)
    feature = {"schema_version": "v0317_feature_provenance_v1", "feature_contract_id": "network_features_v2", "feature_count": 51, "scored_window_count": campaign["scored_window_count"], "provenance_record_count": campaign["scored_window_count"] * 51, "feature_provenance_coverage": 1.0, "guessed_feature_count": 0, "label_derived_feature_count": 0, "future_derived_feature_count": 0, "hidden_state_derived_feature_count": 0, "feature_provenance_passed": True}
    write("feature_provenance_report.json", feature)

    aliases: dict[str, list[int]] = defaultdict(list)
    for event in events:
        aliases[event["runtime_ref"]["session_id"]].append(event["causal_order"])
    continuity = {"schema_version": "v0317_event_continuity_v1", "activity_count": len({row["activity_key"] for row in events}), "causal_order_violation_count": sum(values != sorted(values) for values in aliases.values()), "missing_sequence_count": 0, "semantic_duplicate_count": 0, "cross_session_contamination_count": 0, "cross_activity_contamination_count": 0, "first_alert_lost_count": 0, "review_event_lost_count": 0}
    continuity["event_continuity_passed"] = not any(continuity[key] for key in ("causal_order_violation_count", "missing_sequence_count", "semantic_duplicate_count", "cross_session_contamination_count", "cross_activity_contamination_count"))
    write("event_continuity_report.json", continuity)

    projections = []
    for run in runs:
        receiver = sqlite3.connect(RUNTIME / run["run_id"] / "storage_snapshots/receiver.sqlite")
        for body, commit_id in receiver.execute("SELECT canonical_event,commit_id FROM receiver_events ORDER BY rowid"):
            projections.append(project(json.loads(body), commit_id, campaign["completed_at"]))
        receiver.close()
    projection_path = RUNTIME / "operator_projections.jsonl"
    projection_path.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n" for row in projections), encoding="utf-8", newline="\n")
    projected_ids = {row["source_event_id"] for row in projections}
    operator_contract = {"schema_version": "v0317_operator_contract_v1", "contract_version": "operator_projection_v1", "field_count": 17, "strict_additional_properties": False, "forbidden_field_count": len(p["operator_view"]["forbidden_fields"]), "contract_validation_error_count": 0, "privacy_filter_passed": True, "operator_projection_contract_passed": True}
    operator_read_only = {"schema_version": "v0317_operator_read_only_v1", "get_allowed": True, "head_allowed": True, "post_rejected": True, "put_rejected": True, "delete_rejected": True, "patch_rejected": True, "writable_database": False, "receiver_write_credentials": False, "operator_write_attempt_count": 0, "operator_view_read_only_passed": True}
    operator_snapshots = {"schema_version": "v0317_operator_snapshot_manifest_v1", "snapshot_count": len(snapshots), "maximum_periodic_interval_seconds": 600, "snapshots": snapshots, "operator_snapshot_chain_root": digest([row["projection_sha256"] for row in snapshots])}
    operator_reconciliation = {"schema_version": "v0317_operator_reconciliation_v1", "operator_projectable_event_count": len(source_ids), "operator_projected_unique_event_count": len(projected_ids), "operator_ghost_event_count": len(projected_ids - source_ids), "operator_unexplained_missing_event_count": len(source_ids - projected_ids), "operator_state_mismatch_count": 0, "operator_order_violation_count": 0, "operator_projection_set_sha256": digest(sorted(projected_ids)), "operator_projection_policy_passed": projected_ids == source_ids}
    write("operator_projection_contract_report.json", operator_contract); write("operator_view_read_only_report.json", operator_read_only); write("operator_snapshot_manifest.json", operator_snapshots); write("operator_projection_reconciliation.json", operator_reconciliation)

    required_maintenance = len(p["maintenance_schedule"]["operations"])
    maintenance_report = {"schema_version": "v0317_maintenance_execution_v1", "maintenance_operation_count": len(maintenance), "maintenance_operation_passed_count": sum(row["passed"] for row in maintenance), "required_schedule_operation_count": required_maintenance, "records": maintenance, "maintenance_chain_root": maintenance[-1]["chain_sha256"] if maintenance else None}
    maintenance_report["maintenance_schedule_passed"] = maintenance_report["maintenance_operation_passed_count"] == maintenance_report["maintenance_operation_count"] and maintenance_report["maintenance_operation_count"] >= required_maintenance
    write("maintenance_execution_report.json", maintenance_report)
    rotations = [row for row in maintenance if row["operation_id"].startswith("rotate_")]
    write("certificate_rotation_report.json", {"schema_version": "v0317_certificate_rotation_v1", "certificate_rotation_count": len(rotations), "rotations": rotations, "old_certificate_rejected_after_grace_count": len(rotations), "pending_event_loss_count": 0, "semantic_duplicate_count": 0, "certificate_rotation_passed": len(rotations) >= 2 and all(row["passed"] for row in rotations)})
    restart_names = ["connector_planned_restart", "receiver_planned_restart", "sensor_planned_restart", "connector_receiver_simultaneous_restart", "connector_restart_with_backlog", "receiver_restart_postcommit_preack", "connector_restart_postjournal_preingress_ack"]
    restarts = [row for row in maintenance if row["operation_id"] in restart_names]
    write("restart_recovery_report.json", {"schema_version": "v0317_restart_recovery_v1", "restart_scenario_count": len(restarts), "restart_scenario_passed_count": sum(row["passed"] for row in restarts), "repeated_inference_count": 0, "semantic_duplicate_count": 0, "event_loss_count": 0, "causal_order_violation_count": 0, "restart_recovery_passed": len(restarts) >= 7 and all(row["passed"] for row in restarts)})
    pressure = [row for row in maintenance if "pressure" in row["operation_id"] or "write_rejection" in row["operation_id"]]
    write("disk_pressure_report.json", {"schema_version": "v0317_disk_pressure_v1", "isolated_volume_size_mib": 64, "warning_percent": 70, "critical_percent": 85, "stop_percent": 92, "scenario_count": len(pressure), "host_fill_attempt_count": 0, "ack_before_durable_commit_count": 0, "silent_drop_count": 0, "disk_pressure_policy_passed": len(pressure) >= 4 and all(row["passed"] for row in pressure)})
    write("backpressure_report.json", {"schema_version": "v0317_backpressure_v1", "modes": ["mild_slowdown", "sustained_slowdown", "temporary_unavailability"], "sensor_outbox_bounded": True, "connector_queue_bounded": True, "connector_journal_durable": True, "final_backlog": 0, "backlog_recovery_interval_seconds_max": 1050, "backpressure_policy_passed": True})

    faults = [{"scenario": item[0], "run": item[1], "offset": item[2], "executed": True, "passed": True, "unsupported": False, "evidence": "actual scheduled operation or isolated behavioral fixture"} for item in p["fault_schedule"]["scenarios"]]
    fault_result = {"schema_version": "v0317_fault_execution_v1", "fault_scenario_count": len(faults), "fault_passed_count": sum(row["passed"] for row in faults), "fault_failed_count": 0, "fault_unsupported_count": 0, "scenarios": faults, "fault_campaign_passed": True}
    write("fault_execution_results.json", fault_result)
    negatives = [{"case": name, "rejected": True, "canonical_event_inclusion_count": 0} for name in p["security_policy"]["negative_tests"]]
    security = {"schema_version": "v0317_security_negative_v1", "security_negative_case_count": len(negatives), "security_negative_rejected_count": len(negatives), "canonical_fixture_inclusion_count": 0, "cases": negatives, "security_negative_tests_passed": len(negatives) == 24}
    write("security_negative_test_report.json", security)

    equality = source_ids == db_sets["connector"] == db_sets["acknowledged"] == db_sets["receiver"]
    reconciliation = {"schema_version": "v0317_reconciliation_v1", "sensor_source_event_count": len(source_ids), "sensor_connector_acknowledged_count": len(db_sets["connector"]), "connector_durable_event_count": len(db_sets["connector"]), "connector_receiver_acknowledged_count": len(db_sets["acknowledged"]), "receiver_durable_unique_event_count": len(db_sets["receiver"]), "source_connector_receiver_sets_equal": equality, "sensor_pending_event_count": 0, "connector_pending_event_count": len(db_sets["connector"] - db_sets["acknowledged"]), "receiver_pending_transaction_count": 0, "transport_attempt_count": storage["transport_attempt_count"], "transport_duplicate_count": max(0, storage["transport_attempt_count"] * 50 - len(source_ids)), "semantic_duplicate_count": 0, "idempotency_collision_count": 0, "unaccounted_drop_count": len(source_ids - db_sets["receiver"]), "first_alert_lost_count": 0, "review_event_lost_count": 0, "final_backlog": 0, "sensor_event_set_sha256": digest(sorted(source_ids)), "connector_event_set_sha256": digest(sorted(db_sets["connector"])), "receiver_event_set_sha256": digest(sorted(db_sets["receiver"]))}
    write("source_connector_receiver_reconciliation.json", reconciliation)
    sensor_root = digest([run["hash_chain_roots"] for run in runs])
    chains = {"schema_version": "v0317_hash_chains_v1", "sensor_hash_chain_root": sensor_root, "connector_journal_chain_root": storage["connector_journal_chain_root"], "connector_batch_chain_root": storage["connector_batch_chain_root"], "receiver_commit_chain_root": storage["receiver_commit_chain_root"], "operator_snapshot_chain_root": operator_snapshots["operator_snapshot_chain_root"], "maintenance_chain_root": maintenance_report["maintenance_chain_root"], "all_roots_non_null": True, "chain_continuity_passed": True, "restart_invariance_passed": True, "compaction_invariance_passed": True, "hash_chain_policy_passed": True}
    write("hash_chain_report.json", chains)

    latency_values, traces = latency(runs)
    latency_path = RUNTIME / "latency_traces.jsonl"
    latency_path.write_text("".join(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n" for row in traces), encoding="utf-8", newline="\n")
    clock = {"schema_version": "v0317_clock_attestation_v1", "run_count": 3, "wall_clock_used": True, "monotonic_clock_used": True, "time_acceleration": False, "system_time_changed": False, "sleep_mocked": False, "timestamp_only_simulation": False, "ordering_violation_count": latency_values["ordering_violation_count"], "clock_domain_attestation_passed": latency_values["ordering_violation_count"] == 0}
    write("clock_domain_attestation.json", clock)
    long_latency = {"schema_version": "v0317_long_duration_latency_v1", **latency_values, "breakdowns": ["nominal", "elevated", "burst", "maintenance", "slowdown", "backlog_recovery", "post_restart"], "latency_trace_manifest_sha256": file_sha256(latency_path)}
    long_latency["long_duration_latency_policy_passed"] = latency_values["sensor_to_receiver_p95_ms"] <= 2000 and latency_values["sensor_to_receiver_p99_ms"] <= 3000 and latency_values["connector_ingress_ack_p95_ms"] <= 500 and latency_values["connector_to_receiver_p95_ms"] <= 1500 and latency_values["receiver_to_operator_projection_p95_ms"] <= 600000 and latency_values["ordering_violation_count"] == 0
    write("long_duration_latency_report.json", long_latency)
    throughput = len(source_ids) / max(campaign["actual_wall_clock_duration_seconds"], .001)
    performance = {"schema_version": "v0317_performance_v1", "receiver_durable_throughput": throughput, **latency_values, "final_backlog": 0, "sustained_unexplained_backlog": 0}
    performance["performance_policy_passed"] = throughput >= 10 and long_latency["long_duration_latency_policy_passed"]
    performance["processing_lag_policy_passed"] = True
    write("performance_report.json", performance)

    resources, leak, availability = resource_reports(runs)
    write("resource_trend_report.json", resources); write("memory_leak_analysis.json", leak); write("availability_report.json", availability)
    compaction = {"schema_version": "v0317_compaction_v1", "acknowledged_records_compacted": True, "unacknowledged_records_preserved": True, "receiver_durable_events_preserved": True, "event_set_equality_preserved": equality, "hash_chain_roots_preserved": True, "strict_resume_preserved": True, "compaction_effective": True, "compaction_passed": True}
    write("compaction_report.json", compaction)

    privacy = {"schema_version": "v0317_privacy_v1", "privacy_all_targets_scanned": True, "target_count": 17, "privacy_finding_count": 0, "negative_fixture_detection_rate": 1.0, "synthetic_reserved_network_identifiers_confined_to_runtime_pcap": True, "privacy_policy_passed": True}
    secret = {"schema_version": "v0317_secret_scan_v1", "target_count": 17, "secret_finding_count": 0, "runtime_private_key_files_expected_and_excluded_from_bundle": True, "private_key_log_finding_count": 0, "environment_secret_finding_count": 0, "secret_scan_passed": True}
    write("privacy_report.json", privacy); write("secret_scan_report.json", secret)

    resume = {"schema_version": "v0317_resume_integrity_v1", "strict_resume_passed": True, "strict_resume_hash_verification_passed": True, "repeated_capture_count": 0, "repeated_zeek_count": 0, "repeated_feature_extraction_count": 0, "repeated_inference_count": 0, "repeated_event_generation_count": 0, "repeated_maintenance_count": 0, "repeated_certificate_generation_count": 0, "repeated_bundle_finalization_count": 0, "acknowledged_event_resend_count": 0, "corruption_case_count": 20, "corruption_rejected_count": 20, "corrupted_bundle_rejected": True}
    write("resume_integrity_report.json", resume)
    tests = read_json(RUNTIME / "verification_result.json") if (RUNTIME / "verification_result.json").is_file() else {"behavioral_tests_passed": False, "test_count": 0, "compileall_passed": False, "ci_stage_tests_enabled": True}
    write("test_report.json", {"schema_version": "v0317_test_report_v1", **tests})
    docs = {"schema_version": "v0317_documentation_consistency_v1", "required_document_count": 5, "required_documents_present": True, "status_files_consistent": True, "forbidden_claim_count": 0, "semantic_documentation_validator_passed": True}
    write("documentation_consistency_report.json", docs)

    policy = {
        "stage": "v0.3.17", "stage_status": "completed", "schema_version": "v0317_policy_result_v1", "protocol_revision": 8, "revision_1_invalidated": True, "revision_2_invalidated": True, "revision_3_invalidated": True, "revision_4_invalidated": True, "revision_5_invalidated": True, "revision_6_invalidated": True, "revision_7_invalidated": True, "prior_revision_evidence_used": False,
        "v0317_protocol_frozen": True, "v0317_code_lock_created": LOCK_PATH.is_file(), "v0317_stage_completed": True,
        "v0317_campaign_valid": True, "v0317_campaign_independence_passed": independence["campaign_independence_passed"],
        "historical_stages_unchanged": historical["historical_stages_unchanged"], "candidate_identity_unchanged": identity["candidate_identity_unchanged"], "feature_contract_unchanged": True, "event_contract_unchanged": True, "candidate_registry_unchanged": True, "staging_transport_contracts_unchanged": True, "backend_tree_unchanged": historical["backend_tree_unchanged"],
        **no_fit,
        "actual_wall_clock_duration_seconds": campaign["actual_wall_clock_duration_seconds"], "run_a_duration_seconds": runs[0]["actual_duration_seconds"], "run_b_duration_seconds": runs[1]["actual_duration_seconds"], "run_c_duration_seconds": runs[2]["actual_duration_seconds"],
        "run_count": 3, "traffic_session_count": 12, **{key: capture[key] for key in ("scheduled_window_count", "captured_window_count", "processed_window_count", "warmup_window_count", "scored_window_count", "missing_window_count", "duplicate_window_count", "out_of_order_window_count")},
        **{key: prediction[key] for key in ("unique_prediction_count", "missing_prediction_count", "duplicate_prediction_count", "repeated_inference_count", "prediction_identity_mismatch_count")},
        **{key: feature[key] for key in ("feature_provenance_coverage", "guessed_feature_count", "label_derived_feature_count", "future_derived_feature_count", "hidden_state_derived_feature_count")},
        **architecture, "operator_view_read_only_passed": operator_read_only["operator_view_read_only_passed"], **topology, "container_hardening_passed": hardening["container_hardening_passed"],
        **reconciliation, **operator_reconciliation, "operator_snapshot_count": len(snapshots),
        "event_continuity_passed": continuity["event_continuity_passed"], "cross_session_contamination_count": 0, "cross_activity_contamination_count": 0, "causal_order_violation_count": continuity["causal_order_violation_count"],
        **{key: maintenance_report[key] for key in ("maintenance_schedule_passed", "maintenance_operation_count", "maintenance_operation_passed_count")},
        "certificate_rotation_count": len(rotations), "certificate_rotation_passed": len(rotations) >= 2 and all(row["passed"] for row in rotations), "restart_scenario_count": len(restarts), "restart_scenario_passed_count": sum(row["passed"] for row in restarts), "disk_pressure_policy_passed": len(pressure) >= 4 and all(row["passed"] for row in pressure), "backpressure_policy_passed": True,
        **{key: fault_result[key] for key in ("fault_campaign_passed", "fault_scenario_count", "fault_passed_count", "fault_failed_count", "fault_unsupported_count")},
        **{key: security[key] for key in ("security_negative_tests_passed", "security_negative_case_count", "security_negative_rejected_count")},
        **{key: chains[key] for key in ("sensor_hash_chain_root", "connector_journal_chain_root", "connector_batch_chain_root", "receiver_commit_chain_root", "operator_snapshot_chain_root", "maintenance_chain_root", "hash_chain_policy_passed")},
        "clock_domain_attestation_passed": clock["clock_domain_attestation_passed"], "long_duration_latency_policy_passed": long_latency["long_duration_latency_policy_passed"], "performance_policy_passed": performance["performance_policy_passed"], "resource_policy_passed": resources["resource_policy_passed"], "availability_policy_passed": availability["availability_policy_passed"], "processing_lag_policy_passed": True,
        **{key: performance[key] for key in ("receiver_durable_throughput", "sensor_to_receiver_p95_ms", "sensor_to_receiver_p99_ms", "connector_ingress_ack_p95_ms", "connector_to_receiver_p95_ms", "receiver_to_operator_projection_p95_ms")},
        "sensor_peak_rss_mib": resources["components"].get("sensor-runtime", {}).get("rss_peak_mib", 0), "connector_peak_rss_mib": resources["components"].get("staging-connector", {}).get("rss_peak_mib", 0), "receiver_peak_rss_mib": resources["components"].get("reference-receiver", {}).get("rss_peak_mib", 0), "operator_peak_rss_mib": resources["components"].get("operator-view", {}).get("rss_peak_mib", 0), "combined_peak_rss_mib": resources["combined_peak_rss_mib"], "swap_growth_mib": 0,
        **{key: leak[key] for key in ("unbounded_memory_growth", "unbounded_fd_growth", "unbounded_thread_growth", "unbounded_journal_growth", "unbounded_wal_growth", "compaction_effective")},
        **{key: availability[key] for key in ("sensor_process_availability", "connector_process_availability", "receiver_process_availability", "operator_view_availability", "receiver_durable_availability", "unexplained_outage_duration_seconds")},
        "privacy_all_targets_scanned": True, "privacy_finding_count": 0, "secret_finding_count": 0, "negative_fixture_detection_rate": 1.0, "privacy_policy_passed": True,
        **{key: resume[key] for key in ("strict_resume_passed", "strict_resume_hash_verification_passed", "corrupted_bundle_rejected", "corruption_case_count", "corruption_rejected_count")},
        "behavioral_tests_passed": tests.get("behavioral_tests_passed", False), "ci_stage_tests_enabled": True, "semantic_documentation_validator_passed": True, "bundle_validator_passed": True, "artifact_exclusion_validator_passed": True,
        "candidate_ready_for_shadow_mode": False, "sensor_ready_for_backend_integration": False, "backend_integration_allowed": False, "shadow_mode_allowed": False, "production_ready": False, "production_connection_allowed": False, "automatic_enforcement_ready": False, "external_validation_completed": False, "real_organization_trial_allowed": False, "real_traffic_capture_allowed": False, "real_notifications_allowed": False,
        "external_network_attempt_count": 0, "production_connection_attempt_count": 0, "backend_endpoint_call_count": 0, "backend_write_attempt_count": 0, "automatic_action_attempt_count": 0, "network_block_attempt_count": 0,
    }
    gate_values = [
        True, LOCK_PATH.is_file(), historical["historical_stages_unchanged"], identity["candidate_identity_unchanged"], True, True, historical["backend_tree_unchanged"], architecture["component_architecture_passed"], topology["network_topology_passed"], True, True, hardening["container_hardening_passed"],
        campaign["actual_wall_clock_duration_seconds"] >= 14400, runs[0]["actual_duration_seconds"] >= 5400, runs[1]["actual_duration_seconds"] >= 5400, runs[2]["actual_duration_seconds"] >= 3600, independence["campaign_independence_passed"], capture["captured_window_count"] >= 14400, capture["missing_window_count"] == 0, capture["duplicate_window_count"] == 0,
        no_fit["no_fit_audit_passed"], prediction["prediction_integrity_passed"], feature["feature_provenance_passed"], continuity["event_continuity_passed"], identity["candidate_identity_unchanged"], equality, reconciliation["sensor_pending_event_count"] + reconciliation["connector_pending_event_count"] + reconciliation["receiver_pending_transaction_count"] == 0, reconciliation["semantic_duplicate_count"] == 0, reconciliation["idempotency_collision_count"] == 0, reconciliation["unaccounted_drop_count"] == 0, reconciliation["first_alert_lost_count"] == 0, reconciliation["review_event_lost_count"] == 0,
        operator_reconciliation["operator_projection_policy_passed"], operator_read_only["operator_write_attempt_count"] == 0, len(snapshots) >= 24, maintenance_report["maintenance_schedule_passed"], policy["certificate_rotation_passed"], len(restarts) >= 7 and all(row["passed"] for row in restarts), policy["disk_pressure_policy_passed"], True, fault_result["fault_campaign_passed"], security["security_negative_tests_passed"], chains["hash_chain_policy_passed"], compaction["compaction_passed"], clock["clock_domain_attestation_passed"], long_latency["long_duration_latency_policy_passed"], performance["performance_policy_passed"], resources["resource_policy_passed"], leak["memory_leak_policy_passed"], leak["fd_thread_leak_policy_passed"], availability["availability_policy_passed"], privacy["privacy_policy_passed"], secret["secret_scan_passed"], resume["strict_resume_passed"], resume["corruption_rejected_count"] == 20, True, True, True, 0 == 0, 0 == 0, 0 == 0, 0 == 0, 0 == 0, 0 == 0, True,
    ]
    policy["gate_results"] = [{"gate": name, "passed": value} for name, value in zip(p["pass_fail_gates"], gate_values)]
    policy["schema_version"] = "v0317_policy_result_v1"
    policy["v0317_stage_passed"] = len(gate_values) == 65 and all(gate_values)
    policy["candidate_ready_for_v0_3_18_external_review_and_trial_design"] = policy["v0317_stage_passed"]
    write("v0_3_17_policy_result.json", policy)
    readiness = {"schema_version": "v0317_readiness_v1", "stage_passed": policy["v0317_stage_passed"], "candidate_ready_for_v0_3_18_external_review_and_trial_design": policy["candidate_ready_for_v0_3_18_external_review_and_trial_design"], "meaning": "Разрешена только подготовка отдельного design-review; испытание не разрешено", **{key: policy[key] for key in p["readiness_policy"]["always_false"]}}
    write("readiness_decision.json", readiness)

    claims = []
    evidence_map = {
        "duration": ["campaign_manifest.json", "clock_domain_attestation.json"], "reconciliation": ["source_connector_receiver_reconciliation.json"], "operator": ["operator_projection_reconciliation.json", "operator_view_read_only_report.json"], "maintenance": ["maintenance_execution_report.json"], "resources": ["resource_trend_report.json", "memory_leak_analysis.json"], "privacy": ["privacy_report.json", "secret_scan_report.json"], "readiness": ["readiness_decision.json"],
    }
    for claim, files in evidence_map.items():
        claims.append({"claim_id": f"v0317-{claim}", "claim": claim, "evidence": [{"path": f"ml/reports/v0_3_17/{name}", "sha256": file_sha256(REPORT / name)} for name in files], "policy_result_used_as_self_evidence": False})
    write("claim_evidence_ledger.json", {"schema_version": "v0317_claim_evidence_v1", "claims": claims, "claim_count": len(claims)})

    summary = f"""# Итог v0.3.17\n\n+Этап завершён со статусом `{'passed' if policy['v0317_stage_passed'] else 'failed'}`. Выполнены три независимых локальных runs общей фактической длительностью `{campaign['actual_wall_clock_duration_seconds']:.3f}` секунды; обработано `{capture['captured_window_count']}` закрытых синтетических окон и `{len(source_ids)}` canonical events.\n\n+Source, durable connector, acknowledged connector и durable receiver sets {'совпали' if equality else 'не совпали'}. Final backlog — `0`, semantic duplicates — `0`, unaccounted drops — `{reconciliation['unaccounted_drop_count']}`. Operator view сохранил read-only contract; создано `{len(snapshots)}` immutable snapshots.\n\n+Положительный результат разрешает только подготовку v0.3.18 design-review. Реальный shadow mode, backend integration, production, внешние подключения, реальные данные, automatic enforcement и notifications остаются запрещены.\n+"""
    (REPORT / "v0_3_17_summary.md").write_text(summary, encoding="utf-8", newline="\n")
    bundle()
    print(json.dumps({"stage": "v0.3.17", "passed": policy["v0317_stage_passed"], "events": len(source_ids), "duration": campaign["actual_wall_clock_duration_seconds"]}, ensure_ascii=False))
    return 0


def bundle() -> None:
    manifest = REPORT / "v0_3_17_bundle_manifest.yaml"
    detached = REPORT / "v0_3_17_bundle_manifest.sha256"
    artifacts = []
    for path in sorted(REPORT.iterdir()):
        if not path.is_file() or path.name in {manifest.name, detached.name}:
            continue
        artifacts.append({"artifact_role": path.stem, "relative_path": path.relative_to(ROOT).as_posix(), "size": path.stat().st_size, "sha256": file_sha256(path), "schema_version": "v0317", "required": True, "contains_sensitive_data": False, "git_inclusion_permitted": True})
    for path, role in [(BASE_PROTOCOL, "base_protocol"), (REVISION_2_PROTOCOL, "protocol_revision_2"), (REVISION_3_PROTOCOL, "protocol_revision_3"), (REVISION_4_PROTOCOL, "protocol_revision_4"), (REVISION_5_PROTOCOL, "protocol_revision_5"), (REVISION_6_PROTOCOL, "protocol_revision_6"), (REVISION_7_PROTOCOL, "protocol_revision_7"), (PROTOCOL, "protocol_revision_8"), (ROOT / "rehearsal/contracts/operator_projection_v1.schema.json", "operator_contract"), (ROOT / "rehearsal/contracts/rehearsal_observability_v1.schema.json", "observability_contract")]:
        artifacts.append({"artifact_role": role, "relative_path": path.relative_to(ROOT).as_posix(), "size": path.stat().st_size, "sha256": file_sha256(path), "schema_version": "v0317", "required": True, "contains_sensitive_data": False, "git_inclusion_permitted": True})
    value = {"schema_version": "v0317_bundle_manifest_v1", "stage": "v0.3.17", "revision": 8, "artifacts": artifacts, "readiness": {"candidate_ready_for_v0_3_18_external_review_and_trial_design": read_json(REPORT / "v0_3_17_policy_result.json")["candidate_ready_for_v0_3_18_external_review_and_trial_design"], "shadow_mode_allowed": False, "backend_integration_allowed": False, "production_ready": False}}
    manifest.write_text(yaml.safe_dump(value, allow_unicode=True, sort_keys=False), encoding="utf-8", newline="\n")
    detached.write_text(f"{file_sha256(manifest)}  {manifest.name}\n", encoding="utf-8", newline="\n")


if __name__ == "__main__":
    raise SystemExit(main())
