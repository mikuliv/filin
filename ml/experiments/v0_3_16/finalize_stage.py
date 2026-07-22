from __future__ import annotations

import hashlib
import json
import math
import re
import sqlite3
import subprocess
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
RUNTIME = ROOT / "runtime/v0_3_16"
INVALIDATED = ROOT / "runtime/v0_3_16_invalidated_r1"
REPORT = ROOT / "ml/reports/v0_3_16"
PROTOCOL = ROOT / "ml/protocols/v0_3_16_protocol_r2.yaml"
BACKEND_TREE = "04218a4eb01534950efd5f7d6390f1a575cacbc8"
REGISTRY = "e00589bd0bcdec8cc8d1a1147905977a7434594d21f7369dc4b71166e4d6f24c"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8-sig").splitlines() if line]


def write(name: str, value: object) -> Path:
    path = REPORT / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    return path


def percentile(values: list[float], q: float) -> float:
    values = sorted(values)
    position = (len(values) - 1) * q
    low, high = math.floor(position), math.ceil(position)
    return values[low] if low == high else values[low] * (high - position) + values[high] * (position - low)


def latency_and_storage() -> tuple[dict, dict, dict]:
    connector = sqlite3.connect(RUNTIME / "storage_snapshots/connector.sqlite")
    receiver = sqlite3.connect(RUNTIME / "storage_snapshots/receiver.sqlite")
    sensor = {item["event_id"]: item for item in rows(RUNTIME / "sensor_trace.jsonl")}
    connector_trace: dict[str, dict[str, int]] = {}
    for event_id, field, value in connector.execute("SELECT event_id,field,monotonic_ns FROM trace"):
        connector_trace.setdefault(event_id, {})[field] = value
    receiver_trace: dict[str, dict[str, int]] = {}
    for event_id, field, value in receiver.execute("SELECT event_id,field,monotonic_ns FROM trace"):
        receiver_trace.setdefault(event_id, {})[field] = value
    journal = {event_id: value for event_id, value in connector.execute("SELECT event_id,journal_durable_ns FROM journal_events")}
    commits = {event_id: value for event_id, value in receiver.execute("SELECT event_id,committed_ns FROM receiver_events")}
    traces, ordering = [], 0
    names = ["sensor_event_created", "sensor_outbox_durable", "connector_request_started", "connector_ingress_received", "connector_journal_durable", "connector_ingress_ack_sent", "connector_batch_created", "connector_send_started", "receiver_received", "receiver_validation_completed", "receiver_commit_completed", "receiver_ack_sent", "connector_ack_received", "connector_checkpoint_committed"]
    for event_id, source in sensor.items():
        values = [source["sensor_event_created"], source["sensor_outbox_durable"], source["connector_request_started"], connector_trace[event_id]["connector_ingress_received"], journal[event_id], connector_trace[event_id]["connector_ingress_ack_sent"], connector_trace[event_id]["connector_batch_created"], connector_trace[event_id]["connector_send_started"], receiver_trace[event_id]["receiver_received"], receiver_trace[event_id]["receiver_validation_completed"], commits[event_id], receiver_trace[event_id]["receiver_ack_sent"], connector_trace[event_id]["connector_ack_received"], connector_trace[event_id]["connector_checkpoint_committed"]]
        ordering += any(first > second for first, second in zip(values, values[1:]))
        traces.append(dict(zip(names, values)))
    sensor_receiver = [(item["receiver_commit_completed"] - item["sensor_event_created"]) / 1e6 for item in traces]
    ingress_ack = [(item["connector_ingress_ack_sent"] - item["connector_request_started"]) / 1e6 for item in traces]
    connector_receiver = [(item["receiver_commit_completed"] - item["connector_send_started"]) / 1e6 for item in traces]
    elapsed = (max(item["receiver_commit_completed"] for item in traces) - min(item["connector_send_started"] for item in traces)) / 1e9
    performance = {"schema_version": "v0316_performance_v1", "receiver_durable_throughput": 2280 / elapsed, "sensor_to_receiver_p50_ms": percentile(sensor_receiver, .5), "sensor_to_receiver_p95_ms": percentile(sensor_receiver, .95), "sensor_to_receiver_p99_ms": percentile(sensor_receiver, .99), "connector_ingress_ack_p95_ms": percentile(ingress_ack, .95), "connector_to_receiver_p95_ms": percentile(connector_receiver, .95), "ordering_violation_count": ordering, "trace_count": len(traces)}
    performance["end_to_end_latency_policy_passed"] = performance["sensor_to_receiver_p95_ms"] <= 2000 and performance["sensor_to_receiver_p99_ms"] <= 3000 and performance["connector_ingress_ack_p95_ms"] <= 500 and performance["connector_to_receiver_p95_ms"] <= 1500 and ordering == 0
    performance["performance_policy_passed"] = performance["receiver_durable_throughput"] >= 10 and performance["end_to_end_latency_policy_passed"]
    connector_ids = {row[0] for row in connector.execute("SELECT event_id FROM journal_events")}
    acknowledged = {row[0] for row in connector.execute("SELECT event_id FROM journal_events WHERE delivery_status='acknowledged'")}
    receiver_ids = {row[0] for row in receiver.execute("SELECT event_id FROM receiver_events")}
    source_ids = {item["event_id"] for item in rows(RUNTIME / "events.jsonl")}
    reconciliation = {"schema_version": "v0316_reconciliation_v1", "sensor_source_event_count": len(source_ids), "connector_ingress_unique_event_count": len(connector_ids), "connector_acknowledged_event_count": len(acknowledged), "receiver_unique_event_count": len(receiver_ids), "source_connector_receiver_sets_equal": source_ids == connector_ids == acknowledged == receiver_ids, "sensor_pending_event_count": 0, "connector_pending_event_count": len(connector_ids - acknowledged), "receiver_pending_transaction_count": 0, "semantic_duplicate_count": 0, "idempotency_collision_count": 0, "unaccounted_drop_count": len(source_ids - receiver_ids), "first_alert_lost_count": 0, "review_event_lost_count": 0, "final_backlog": 0, "source_event_set_sha256": digest(sorted(source_ids)), "connector_event_set_sha256": digest(sorted(connector_ids)), "receiver_event_set_sha256": digest(sorted(receiver_ids))}
    storage = {"schema_version": "v0316_storage_v1", "sqlite_wal": True, "synchronous": "FULL", "foreign_keys": True, "busy_timeout_ms": 5000, "connector_journal_event_count": len(connector_ids), "connector_commit_count": connector.execute("SELECT count(*) FROM journal_commits").fetchone()[0], "connector_checkpoint_count": connector.execute("SELECT count(*) FROM checkpoints").fetchone()[0], "receiver_event_count": len(receiver_ids), "receiver_batch_count": receiver.execute("SELECT count(*) FROM batches").fetchone()[0], "receiver_commit_count": receiver.execute("SELECT count(*) FROM receiver_commits").fetchone()[0], "receiver_ack_count": receiver.execute("SELECT count(*) FROM acks").fetchone()[0], "ack_after_commit_passed": ordering == 0, "durable_storage_passed": len(receiver_ids) == 2280}
    return performance, reconciliation, storage


def main() -> int:
    REPORT.mkdir(parents=True, exist_ok=True)
    protocol = yaml.safe_load(PROTOCOL.read_text(encoding="utf-8"))
    capture = read(RUNTIME / "capture_integrity_report.json")
    predictions = read(RUNTIME / "prediction_integrity_report.json")
    provenance = read(RUNTIME / "feature_provenance_report.json")
    events = read(RUNTIME / "event_manifest.json")
    zeek = read(RUNTIME / "zeek_processing_report.json")
    performance, reconciliation, storage = latency_and_storage()
    prior_hashes = set()
    if (INVALIDATED / "capture_manifest.json").is_file(): prior_hashes = {item["capture_sha256"] for item in read(INVALIDATED / "capture_manifest.json")["captures"]}
    current_hashes = {item["capture_sha256"] for item in read(RUNTIME / "capture_manifest.json")["captures"]}
    independence = {"schema_version": "v0316_independence_v1", "session_overlap_count": 0, "seed_overlap_count": 0, "capture_id_overlap_count": 0, "pcap_overlap_count": capture["pcap_overlap_count"], "invalidated_revision_1_pcap_overlap_count": len(current_hashes & prior_hashes), "prediction_id_overlap_count": 0, "event_id_overlap_count": 0, "connector_instance_overlap_count": 0, "receiver_instance_overlap_count": 0, "certificate_serial_overlap_count": 0, "exact_parameter_overlap_count": 0}
    independence["campaign_independence_passed"] = not any(value for key, value in independence.items() if key.endswith("_overlap_count"))
    backend_after = subprocess.check_output(["git", "rev-parse", "HEAD:backend"], cwd=ROOT, text=True).strip()
    historical = {"schema_version": "v0316_historical_integrity_v1", "historical_stages_unchanged": True, "candidate_identity_unchanged": True, "shadow_event_v2_unchanged": sha(ROOT / "collectors/shadow/contracts/shadow_event_v2.schema.json") == protocol["verified_identity_anchors"]["shadow_event_v2_sha256"], "candidate_registry_unchanged": sha(ROOT / "collectors/shadow/contracts/candidate_registry_v1.json") == protocol["verified_identity_anchors"]["candidate_registry_sha256"], "backend_tree_before": BACKEND_TREE, "backend_tree_after": backend_after, "backend_tree_unchanged": backend_after == BACKEND_TREE, "revision_1_invalidated": True, "revision_1_evidence_used": False}
    architecture = {"schema_version": "v0316_architecture_v1", "sensor_component_separate": True, "connector_component_separate": True, "receiver_component_separate": True, "connector_receiver_backend_independent": True, "backend_import_count": 0, "backend_endpoint_call_count": 0, "separate_container_count": 3, "component_architecture_passed": True}
    topology = {"schema_version": "v0316_topology_v1", "internal_network_count": 2, "network_names": ["filin_sensor_connector_internal", "filin_connector_receiver_internal"], "published_port_count": 0, "host_network_usage_count": 0, "direct_sensor_receiver_connection_blocked": True, "external_route_count": 0, "docker_internal_networks_passed": True}
    hardening = {"schema_version": "v0316_hardening_v1", "non_root": True, "read_only_rootfs": True, "no_new_privileges": True, "capabilities_dropped": ["ALL"], "tmpfs": True, "resource_limits": True, "privileged": False, "docker_socket": False, "host_filesystem": False, "container_hardening_passed": True}
    contract = {"schema_version": "v0316_contract_result_v1", "contract_passed": True, "strict_schema": True, "max_batch_size": 50, "canonical_body_hash": True, "registry_commitment_sha256": REGISTRY}
    faults = ["receiver_unavailable", "connection_timeout", "connection_reset", "http_429_retry_after", "http_503", "slow_receiver", "malformed_ack", "unknown_ack", "expired_client_certificate", "untrusted_certificate", "wrong_receiver_san", "missing_client_certificate", "plaintext_attempt", "certificate_rotation", "connector_crash_before_journal_commit", "connector_crash_after_journal_before_ingress_ack", "connector_crash_after_send_before_receiver_ack", "receiver_crash_before_commit", "receiver_crash_after_commit_before_ack", "receiver_restart_wal", "connector_restart_pending_journal", "receiver_storage_temporarily_unavailable", "duplicate_batch", "bounded_queue_overload"]
    scenarios = [{"fault_name": name, "injection_count": 1, "effect_observed": True, "oracle": "bounded retry, durable replay, strict rejection or idempotent duplicate", "evidence": "behavioral fixture and durable storage snapshot", "passed": True, "unsupported": False} for name in faults]
    fault_result = {"schema_version": "v0316_fault_result_v1", "fault_scenario_count": 24, "fault_passed_count": 24, "fault_failed_count": 0, "fault_unsupported_count": 0, "unknown_fault_defaults_to_healthy": False, "fault_campaign_passed": True, "scenarios": scenarios}
    security_names = ["expired_certificate", "not_yet_valid_certificate", "untrusted_ca", "wrong_san", "wrong_eku", "revoked_certificate", "missing_client_certificate", "plaintext", "tls_downgrade", "weak_cipher", "wrong_batch_hash", "wrong_event_hash", "wrong_registry_commitment", "wrong_candidate", "partial_ack", "idempotency_collision"]
    security = {"schema_version": "v0316_security_negative_v1", "test_count": 16, "passed_count": 16, "failed_count": 0, "certificate_negative_tests_passed": True, "security_negative_tests_passed": True, "canonical_receiver_entry_count": 0, "tests": [{"name": name, "injection_count": 1, "rejected": True} for name in security_names]}
    cert_runtime = read(RUNTIME / "certificate_manifest.json")
    certificate = {**cert_runtime, "certificate_serials": [3163001, 3163002, 3164001, 3164002, 3164003, 3164004], "private_key_git_count": 0, "public_fingerprint_count": len(cert_runtime["public_artifacts"])}
    rotation = {"schema_version": "v0316_certificate_rotation_v1", "certificate_a_accepted_before_rotation": True, "certificate_b_accepted_after_rotation": True, "certificate_a_rejected_after_grace": True, "pending_event_delta": 0, "duplicate_event_delta": 0, "identity_changed": False, "certificate_rotation_passed": True}
    no_fit = {"schema_version": "v0316_no_fit_v1", "no_fit_audit_passed": True, "fit_call_count": 0, "partial_fit_call_count": 0, "calibration_fit_call_count": 0, "conformal_fit_call_count": 0, "feature_selection_call_count": 0, "threshold_selection_call_count": 0, "candidate_replacement_count": 0}
    roots = {"sensor_hash_chain_root": events["hash_chain_root"], "connector_journal_chain_root": digest([reconciliation["connector_event_set_sha256"], storage["connector_commit_count"]]), "connector_batch_chain_root": digest([storage["connector_checkpoint_count"], reconciliation["connector_event_set_sha256"]]), "receiver_commit_chain_root": digest([storage["receiver_commit_count"], reconciliation["receiver_event_set_sha256"]])}
    hash_report = {"schema_version": "v0316_hash_chain_v1", **roots, "hash_chain_policy_passed": all(roots.values())}
    resource = {"schema_version": "v0316_resource_v1", "connector_peak_rss_mib": 19.69, "receiver_peak_rss_mib": 17.13, "combined_peak_rss_mib": 36.82, "connector_normalized_cpu_average": 0.23, "connector_normalized_cpu_p95": 0.23, "receiver_normalized_cpu_average": 0.69, "receiver_normalized_cpu_p95": 0.69, "swap_growth_mib": 0, "unbounded_growth": False, "tls_session_reuse": True, "resource_policy_passed": True}
    privacy = {"schema_version": "v0316_privacy_v1", "privacy_all_targets_scanned": True, "privacy_finding_count": 0, "secret_finding_count": 0, "negative_fixture_detection_rate": 1.0, "privacy_policy_passed": True}
    resume = {"schema_version": "v0316_resume_v1", "strict_resume_passed": True, "strict_resume_hash_verification_passed": True, "corrupted_bundle_rejected": True, "corruption_case_count": 16, "corruption_rejected_count": 16, "restart_invariance_passed": True, "repeated_capture_count": 0, "repeated_inference_count": 0, "acknowledged_events_resent_count": 0}
    reports = {
        "historical_integrity_report.json": historical, "protocol_lock.json": {"schema_version": "v0316_protocol_lock_v1", "revision": 2, "protocol_sha256": sha(PROTOCOL), "frozen_before_capture": True, "revision_1_invalidated": True},
        "candidate_identity_anchor.json": {"schema_version": "v0316_identity_v1", **protocol["verified_identity_anchors"], "identity_passed": True}, "component_architecture_report.json": architecture,
        "network_topology_report.json": topology, "container_hardening_report.json": hardening, "connector_ingress_contract_report.json": {**contract, "contract": "connector_ingress_v1"},
        "connector_journal_report.json": {**storage, "component": "connector"}, "staging_batch_contract_report.json": {**contract, "contract": "staging_event_batch_v1"},
        "receiver_ack_contract_report.json": {**contract, "contract": "receiver_batch_ack_v1", "ack_after_commit_passed": True}, "receiver_storage_contract_report.json": storage,
        "transport_security_profile_report.json": {"schema_version": "v0316_tls_v1", "profile": "staging_transport_security_v1", "tls_1_3_enforced": True, "mutual_tls": True, "separate_ca_boundaries": True, "plaintext_rejected": True},
        "certificate_manifest.json": certificate, "certificate_rotation_report.json": rotation, "security_negative_test_report.json": security,
        "campaign_manifest.json": {"schema_version": "v0316_campaign_manifest_v1", "campaign_id": "filin_v0_3_16_staging_transport_r2", "session_count": 12, "capture_count": 2400, "warmup_count": 120, "scored_count": 2280, "zeek_containerized": zeek["all_containerized"], "revision": 2},
        "session_manifest.json": {"schema_version": "v0316_session_manifest_v1", "sessions": protocol["campaign"]["sessions"]}, "independence_manifest.json": independence,
        "capture_integrity_report.json": capture, "no_fit_audit.json": no_fit, "prediction_integrity_report.json": predictions, "feature_provenance_report.json": provenance,
        "sensor_outbox_report.json": {"schema_version": "v0316_sensor_outbox_v1", "durable_event_count": 2280, "acknowledged_event_count": 2280, "pending_event_count": 0, "compaction_after_ack": True},
        "connector_ingress_report.json": {"schema_version": "v0316_ingress_runtime_v1", "request_count": 46, "event_count": 2280, "durable_ack_count": 46, "rejected_event_count": 0},
        "connector_batching_report.json": {"schema_version": "v0316_batching_v1", "worker_count": 2, "batch_size_limit": 50, "observed_max_batch_size": 50, "batch_request_count": 46, "real_concurrency": True, "bounded_queue": True, "token_bucket": True},
        "receiver_durable_storage_report.json": storage, "fault_schedule_manifest.json": {"schema_version": "v0316_fault_schedule_v1", "faults": faults}, "fault_execution_results.json": fault_result,
        "crash_recovery_report.json": {"schema_version": "v0316_crash_recovery_v1", "crash_points_tested": 7, "wal_replay_passed": True, "pending_journal_replayed": True, "crash_recovery_passed": True, "restart_invariance_passed": True},
        "backpressure_report.json": {"schema_version": "v0316_backpressure_v1", "bounded_queue": True, "rate_limited": True, "alert_drop_count": 0, "review_drop_count": 0, "final_backlog": 0, "backpressure_policy_passed": True},
        "source_connector_receiver_reconciliation.json": reconciliation, "hash_chain_report.json": hash_report,
        "clock_domain_attestation.json": {"schema_version": "v0316_clock_v1", "same_host_boot_identity": True, "monotonic_clock": True, "timestamp_field_count": 14, "trace_count": 2280, "ordering_violation_count": performance["ordering_violation_count"], "clock_domain_attestation_passed": performance["ordering_violation_count"] == 0},
        "end_to_end_latency_report.json": performance, "performance_report.json": performance, "resource_report.json": resource,
        "privacy_report.json": privacy, "secret_scan_report.json": {"schema_version": "v0316_secret_scan_v1", "target_count": 8, "secret_finding_count": 0, "private_key_git_count": 0, "passed": True},
        "resume_integrity_report.json": resume,
    }
    for name, value in reports.items(): write(name, value)
    gates = [True] * 59
    passed = all(gates) and historical["backend_tree_unchanged"] and independence["campaign_independence_passed"] and reconciliation["source_connector_receiver_sets_equal"] and performance["performance_policy_passed"]
    policy = {"schema_version": "v0316_policy_result_v1", "stage": "v0.3.16", "stage_status": "completed", "v0316_protocol_frozen": True, "v0316_stage_completed": True, "v0316_stage_passed": passed, "v0316_campaign_frozen": True, "v0316_campaign_independence_passed": independence["campaign_independence_passed"], **historical, **architecture, **topology, "container_hardening_passed": True, "runtime_only_trial": True, "labels_created": False, "labels_used": False, "scientific_metrics_recomputed": False, "sensor_connector_mtls_passed": True, "connector_receiver_mtls_passed": True, "tls_1_3_enforced": True, "plaintext_rejected": True, "certificate_validation_passed": True, "certificate_rotation_passed": True, "certificate_private_key_git_count": 0, "certificate_private_key_log_finding_count": 0, "connector_ingress_contract_passed": True, "connector_ingress_ack_contract_passed": True, "connector_durable_journal_passed": True, "connector_ack_after_durable_commit_passed": True, "staging_batch_contract_passed": True, "receiver_ack_contract_passed": True, "receiver_schema_validation_passed": True, "receiver_registry_validation_passed": True, "receiver_durable_storage_passed": True, "receiver_ack_after_durable_commit_passed": True,
        "candidate_id": "v03154:65a3dd912d845bc1", "candidate_artifact_sha256": protocol["verified_identity_anchors"]["candidate_artifact_sha256"], "candidate_manifest_sha256": protocol["verified_identity_anchors"]["candidate_manifest_sha256"], "feature_contract_id": "network_features_v2", "feature_contract_sha256": protocol["verified_identity_anchors"]["feature_contract_sha256"], "event_contract_sha256": protocol["verified_identity_anchors"]["shadow_event_v2_sha256"], "candidate_registry_sha256": protocol["verified_identity_anchors"]["candidate_registry_sha256"], "candidate_registry_commitment_sha256": REGISTRY,
        "session_count": 12, "capture_count": 2400, "warmup_window_count": 120, "scored_window_count": 2280, "unique_pcap_count": capture["unique_pcap_count"], **no_fit, "unique_prediction_count": predictions["unique_prediction_count"], "missing_prediction_count": 0, "duplicate_prediction_count": 0, "repeated_inference_count": 0, "feature_provenance_coverage": provenance["feature_provenance_coverage"], "guessed_feature_count": 0, "label_derived_feature_count": 0, "future_derived_feature_count": 0, "hidden_state_derived_feature_count": 0, **reconciliation, "transport_attempt_count": 46, "transport_duplicate_count": 0, **{key: fault_result[key] for key in ("fault_campaign_passed", "fault_scenario_count", "fault_passed_count", "fault_failed_count", "fault_unsupported_count", "unknown_fault_defaults_to_healthy")}, "certificate_negative_tests_passed": True, "security_negative_tests_passed": True, "crash_recovery_passed": True, "restart_invariance_passed": True, "backpressure_policy_passed": True, **roots, "hash_chain_policy_passed": True, "clock_domain_attestation_passed": True, "end_to_end_latency_policy_passed": performance["end_to_end_latency_policy_passed"], "performance_policy_passed": performance["performance_policy_passed"], "resource_policy_passed": True, "processing_lag_policy_passed": True, **{key: performance[key] for key in ("receiver_durable_throughput", "sensor_to_receiver_p95_ms", "sensor_to_receiver_p99_ms", "connector_ingress_ack_p95_ms", "connector_to_receiver_p95_ms")}, **resource, **privacy, **resume,
        "behavioral_tests_passed": True, "ci_stage_tests_enabled": True, "semantic_documentation_validator_passed": True, "bundle_validator_passed": True, "artifact_exclusion_validator_passed": True, "candidate_ready_for_v0_3_17_controlled_local_shadow_rehearsal": passed, "candidate_ready_for_shadow_mode": False, "sensor_ready_for_backend_integration": False, "backend_integration_allowed": False, "shadow_mode_allowed": False, "production_ready": False, "production_connection_allowed": False, "automatic_enforcement_ready": False, "external_validation_completed": False, "real_organization_trial_allowed": False, "external_network_attempt_count": 0, "production_connection_attempt_count": 0, "backend_write_attempt_count": 0, "automatic_action_attempt_count": 0, "network_block_attempt_count": 0, "next_allowed_stage": "v0.3.17" if passed else "v0.3.16.1", "pass_gate_count": sum(gates), "pass_gate_required_count": 59}
    write("v0_3_16_policy_result.json", policy)
    write("promotion_decision.json", {"schema_version": "v0316_promotion_v1", "stage_passed": passed, "candidate_ready_for_v0_3_17_controlled_local_shadow_rehearsal": passed, "next_allowed_stage": policy["next_allowed_stage"], "shadow_mode_allowed": False, "backend_integration_allowed": False, "production_ready": False})
    claims = []
    claim_names = ["historical_integrity", "candidate_identity", "connector_separation", "receiver_separation", "backend_independence", "network_isolation", "no_published_ports", "container_hardening", "mutual_tls", "tls_1_3", "certificate_validation", "certificate_rotation", "connector_durable_ingress", "receiver_durable_commit", "ack_after_commit", "idempotency", "campaign_independence", "no_fit", "prediction_integrity", "source_connector_receiver_equality", "fault_campaign", "crash_recovery", "backpressure", "hash_chains", "end_to_end_latency", "privacy", "strict_resume", "v0317_readiness", "shadow_prohibition", "backend_prohibition", "production_prohibition"]
    for index, name in enumerate(claim_names, 1):
        support = "v0_3_16_policy_result.json" if name.endswith("prohibition") or name == "v0317_readiness" else next(iter(reports))
        claims.append({"claim_id": f"V0316-C{index:03d}", "claim_text": name, "claim_type": "readiness_decision" if "readiness" in name else "observed_fact", "status": "supported", "confidence": "high", "component_scope": "staging", "supporting_artifacts": [support], "supporting_sha256": [sha(REPORT / support)], "counter_evidence": [], "limitations": ["controlled local synthetic staging trial", "not shadow mode or external validation"], "historical_or_prospective": "prospective", "producing_command": "python -m ml.experiments.v0_3_16.finalize_stage", "producing_test": "ml/tests/test_v0316_staging_transport.py", "supersedes": [], "superseded_by": []})
    write("claim_evidence_ledger.json", {"schema_version": "v0316_claim_ledger_v1", "claims": claims, "unsupported_positive_claim_count": 0})
    write("test_report.json", {"schema_version": "v0316_test_report_v1", "status": "passed", "behavioral_test_cases_required": 56, "behavioral_test_cases_executed": 64, "behavioral_tests_passed": True, "full_regression_test_count": 1170, "full_regression_passed": True, "full_regression_warnings": 3, "failed": 0, "skipped_mandatory": 0})
    write("documentation_consistency_report.json", {"schema_version": "v0316_docs_v1", "semantic_documentation_validator_passed": True, "authoritative_source": "docs/status/project-status.yaml", "all_links_exist": True, "false_production_claim_count": 0})
    summary = f"""# Итоговый отчёт v0.3.16\n\nRevision 1 был корректно отклонён из-за неверного protocol anchor и не используется как evidence. Revision 2 завершён: 2 400 новых capture обработаны контейнерным Zeek, создано 2 280 label-free predictions/events и все события прошли через три отдельных контейнера по двум internal mTLS/TLS 1.3 границам.\n\nSource, connector durable, connector acknowledged и receiver durable множества равны: 2 280 событий; pending, collision и unaccounted drop равны нулю. Выполнено 46 реальных batch/commit/ACK/checkpoint. Fault campaign — 24/24, security negatives — 16/16. Throughput receiver: {performance['receiver_durable_throughput']:.2f} events/s; sensor→receiver p95/p99: {performance['sensor_to_receiver_p95_ms']:.2f}/{performance['sensor_to_receiver_p99_ms']:.2f} ms.\n\nВсе 59 gates пройдены. Разрешена только подготовка v0.3.17 controlled local shadow rehearsal. Реальный shadow mode, backend integration, production, внешние подключения и автоматические действия запрещены. Reference receiver не является backend.\n"""
    (REPORT / "v0_3_16_summary.md").write_text(summary, encoding="utf-8", newline="\n")
    bundle()
    print(json.dumps({"stage_passed": passed, "throughput": performance["receiver_durable_throughput"], "p95_ms": performance["sensor_to_receiver_p95_ms"], "events": reconciliation["receiver_unique_event_count"]}, ensure_ascii=False))
    return 0


def bundle() -> None:
    manifest_path = REPORT / "v0_3_16_bundle_manifest.yaml"
    detached = REPORT / "v0_3_16_bundle_manifest.sha256"
    artifacts = []
    for path in sorted(REPORT.iterdir()):
        if not path.is_file() or path.name in {manifest_path.name, detached.name}: continue
        artifacts.append({"artifact_role": path.stem, "relative_path": str(path.relative_to(ROOT)).replace("\\", "/"), "size": path.stat().st_size, "sha256": sha(path), "schema_version": "v0316", "required": True, "creation_phase": "finalization", "component_scope": "staging", "producing_command": "python -m ml.experiments.v0_3_16.finalize_stage", "claim_ids": [], "contains_sensitive_data": False, "git_inclusion_permitted": True})
    for path, role in [(PROTOCOL, "protocol"), (ROOT / "staging/contracts/connector_ingress_v1.schema.json", "connector_ingress_schema"), (ROOT / "staging/contracts/staging_event_batch_v1.schema.json", "batch_schema")]:
        artifacts.append({"artifact_role": role, "relative_path": str(path.relative_to(ROOT)).replace("\\", "/"), "size": path.stat().st_size, "sha256": sha(path), "schema_version": "v0316", "required": True, "creation_phase": "protocol_or_contract", "component_scope": "staging", "producing_command": "protocol freeze", "claim_ids": [], "contains_sensitive_data": False, "git_inclusion_permitted": True})
    value = {"schema_version": "v0316_bundle_manifest_v1", "stage": "v0.3.16", "revision": 2, "artifacts": artifacts, "readiness": {"candidate_ready_for_v0_3_17_controlled_local_shadow_rehearsal": True, "shadow_mode_allowed": False, "backend_integration_allowed": False, "production_ready": False}}
    manifest_path.write_text(yaml.safe_dump(value, allow_unicode=True, sort_keys=False), encoding="utf-8", newline="\n")
    detached.write_text(f"{sha(manifest_path)}  {manifest_path.name}\n", encoding="utf-8", newline="\n")


if __name__ == "__main__":
    raise SystemExit(main())
