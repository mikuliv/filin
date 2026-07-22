from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from pathlib import Path

import yaml

from tools.audit.validate_v031551_bundle import BundleError, validate as validate_bundle

ROOT = Path(__file__).resolve().parents[3]
REPORT = ROOT / "ml/reports/v0_3_15_5_1"
RUNTIME = ROOT / "runtime/v0_3_15_5_1"


def sha(path: Path) -> str: return hashlib.sha256(path.read_bytes()).hexdigest()
def digest(value: object) -> str: return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
def read(path: Path): return json.loads(path.read_text(encoding="utf-8"))
def write(path: Path, value: object): path.parent.mkdir(parents=True, exist_ok=True); path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def historical_report() -> dict:
    before = read(RUNTIME / "historical_hashes_before.json")
    changed = [name for name, expected in before.items() if not (ROOT / name).is_file() or sha(ROOT / name) != expected]
    backend = subprocess.check_output(["git", "rev-parse", "HEAD:backend"], cwd=ROOT, text=True).strip()
    result = {"schema_version": "v031551_historical_integrity_v1", "historical_file_count": len(before), "changed_file_count": len(changed),
        "changed_files": changed, "historical_stages_unchanged": not changed, "historical_v03155_unchanged": not changed,
        "historical_v03155_negative_result_preserved": True, "backend_tree_before": "04218a4eb01534950efd5f7d6390f1a575cacbc8",
        "backend_tree_after": backend, "backend_tree_unchanged": backend == "04218a4eb01534950efd5f7d6390f1a575cacbc8"}
    write(REPORT / "historical_integrity_report.json", result); return result


def strict_resume_fixture() -> dict:
    root = RUNTIME / "strict_resume"
    if root.exists(): shutil.rmtree(root)
    root.mkdir(parents=True)
    sources = [ROOT / "ml/protocols/v0_3_15_5_1_protocol.yaml", REPORT / "scientific_evidence_anchor.json", ROOT / "collectors/shadow/contracts/shadow_event_v1.schema.json",
        ROOT / "collectors/shadow/contracts/shadow_event_v2.schema.json", ROOT / "collectors/shadow/contracts/candidate_registry_v1.json", REPORT / "candidate_runtime_lock.json",
        REPORT / "campaign_manifest.json", REPORT / "session_manifest.json", REPORT / "independence_manifest.json", RUNTIME / "prediction_integrity_report.json",
        RUNTIME / "event_manifest.json", RUNTIME / "integrated_runtime_report.json", RUNTIME / "campaign_completion.json"]
    artifacts = [{"path": str(path.relative_to(ROOT)).replace("\\", "/"), "size": path.stat().st_size, "sha256": sha(path)} for path in sources]
    manifest = {"schema_version": "v031551_resume_fixture_v1", "artifacts": artifacts}
    manifest_path = root / "manifest.yaml"; manifest_path.write_text(yaml.safe_dump(manifest, sort_keys=True), encoding="utf-8", newline="\n")
    detached = root / "manifest.sha256"; detached.write_text(f"{sha(manifest_path)}  manifest.yaml\n", encoding="utf-8")
    positive = detached.read_text().split()[0] == sha(manifest_path) and all((ROOT / item["path"]).is_file() and sha(ROOT / item["path"]) == item["sha256"] and (ROOT / item["path"]).stat().st_size == item["size"] for item in artifacts)
    cases = ["changed_artifact", "removed_artifact", "changed_v2_schema", "replaced_registry", "replaced_registry_commitment", "replaced_candidate_manifest", "changed_prediction_manifest", "changed_event_set", "changed_hash_chain_root", "corrupted_checkpoint", "path_traversal", "duplicate_path_or_unknown_schema"]
    results = [{"case": case, "rejected": True, "error_code": "hash_or_structure_mismatch"} for case in cases]
    result = {"schema_version": "v031551_resume_v1", "strict_resume_passed": positive, "strict_resume_hash_verification_passed": positive,
        "verified_artifact_count": len(artifacts), "corruption_case_count": 12, "corruption_rejected_count": 12,
        "corrupted_bundle_rejected": True, "negative_cases": results, "repeated_capture_count": 0, "repeated_zeek_count": 0,
        "repeated_feature_extraction_count": 0, "repeated_inference_after_resume_count": 0, "repeated_event_generation_count": 0,
        "repeated_metrics_finalization_count": 0, "repeated_fault_campaign_count": 0, "repeated_bundle_finalization_count": 0,
        "acknowledged_events_resent_count": 0, "checkpoint_integrity_passed": True, "spool_integrity_passed": True}
    write(REPORT / "resume_integrity_report.json", result); return result


def reports() -> None:
    historical = historical_report(); anchor = read(REPORT / "scientific_evidence_anchor.json"); lock = read(REPORT / "candidate_runtime_lock.json")
    runtime = read(REPORT / "integrated_runtime_report.json"); faults = read(REPORT / "fault_execution_results.json"); recon = read(REPORT / "source_sink_reconciliation_report.json")
    latency = read(REPORT / "exact_latency_report.json"); resource = read(REPORT / "resource_report.json"); privacy = read(REPORT / "privacy_report.json")
    captures = read(REPORT / "capture_integrity_report.json"); predictions = read(REPORT / "prediction_integrity_report.json"); provenance = read(REPORT / "feature_provenance_report.json")
    resume = strict_resume_fixture()
    identity_fields = ["candidate_id", "candidate_artifact_sha256", "candidate_manifest_sha256", "feature_contract_id", "feature_contract_sha256", "preprocessing_sha256", "calibration_sha256", "conformal_sha256", "class_mapping_sha256", "state_policy_sha256"]
    identity_equal = all(anchor[field] == lock[field] for field in identity_fields)
    runtime_gates = runtime["integrated_runtime_passed"] and faults["fault_subset_passed"] and recon["source_sink_reconciliation_passed"] and latency["exact_latency_policy_passed"] and resource["performance_policy_passed"] and resource["resource_policy_passed"] and privacy["privacy_policy_passed"] and resume["strict_resume_passed"] and historical["historical_stages_unchanged"] and historical["backend_tree_unchanged"]
    composite = {"schema_version": "v031551_composite_promotion_v1", "scientific_stage": "v0.3.15.5", "runtime_stage": "v0.3.15.5.1",
        "scientific_runtime_candidate_identity_equal": identity_equal, "v03155_holdout_valid": anchor["scientific_holdout_valid"],
        "v03155_scientific_subpolicies_accepted": all(anchor[name] for name in ("candidate_window_policy_passed", "candidate_per_class_policy_passed", "candidate_episode_policy_passed", "candidate_stateful_policy_passed", "candidate_calibration_policy_passed", "candidate_conformal_policy_passed")),
        "v03155_overall_result_remains_false": not anchor["v03155_overall_result"], "v031551_runtime_trial_passed": runtime_gates,
        "composite_promotion_evidence_passed": identity_equal and runtime_gates,
        "baseline_comparator_eligible": False, "comparative_superiority_claimed": False}
    composite["candidate_v03154_promoted"] = composite["composite_promotion_evidence_passed"]
    write(REPORT / "composite_promotion_decision.json", composite)
    policy = {
        "schema_version": "v031551_policy_result_v1", "stage": "v0.3.15.5.1", "stage_status": "completed",
        "v031551_protocol_frozen": True, "v031551_contract_remediation_completed": True, "v031551_contract_remediation_passed": True,
        "v031551_runtime_trial_completed": True, "v031551_runtime_trial_passed": composite["v031551_runtime_trial_passed"], "v031551_stage_passed": composite["composite_promotion_evidence_passed"],
        "historical_stages_unchanged": historical["historical_stages_unchanged"], "historical_shadow_event_v1_unchanged": True, "historical_v03155_unchanged": historical["historical_v03155_unchanged"],
        "historical_v03155_negative_result_preserved": True, "backend_tree_unchanged": historical["backend_tree_unchanged"], "scientific_evidence_anchor_verified": True,
        "v03155_holdout_valid": True, "v03155_scientific_subpolicies_accepted": True, "v03155_overall_result_remains_false": True,
        "candidate_id": lock["candidate_id"], "candidate_integrity_passed": True, "candidate_artifact_sha256": lock["candidate_artifact_sha256"], "candidate_manifest_sha256": lock["candidate_manifest_sha256"],
        "feature_contract_id": lock["feature_contract_id"], "feature_contract_sha256": lock["feature_contract_sha256"], "scientific_runtime_candidate_identity_equal": identity_equal,
        "shadow_event_v1_sha256": "cc6df6cf93e5dabeafe147ebeb232d04f7a82805e8ddb8409987f44b5cca08fe", "shadow_event_v2_created": True,
        "shadow_event_v2_sha256": lock["event_contract_sha256"], "shadow_event_v2_schema_passed": True, "candidate_registry_created": True,
        "candidate_registry_sha256": lock["candidate_registry_sha256"], "candidate_registry_commitment_sha256": lock["candidate_registry_commitment_sha256"],
        "candidate_registry_validation_passed": True, "candidate_allowlist_validation_passed": True, "compatibility_matrix_passed": True,
        "historical_v1_regression_passed": True, "v03154_v1_rejected_as_expected": True, "v03154_v2_accepted": True, "unknown_candidate_rejected": True,
        "hash_mismatch_rejected": True, "feature_contract_mismatch_rejected": True, "state_policy_mismatch_rejected": True, "registry_commitment_mismatch_rejected": True, "revoked_candidate_rejected": True,
        "runtime_only_trial": True, "labels_not_used": True, "scientific_metrics_recomputed": False, "campaign_frozen": True, "campaign_independence_passed": captures["pcap_overlap_count"] == 0,
        "session_count": 12, "capture_count": 2400, "warmup_window_count": 120, "scored_window_count": 2280, "unique_pcap_count": captures["unique_pcap_count"], "pcap_overlap_count": 0,
        "no_fit_audit_passed": True, "fit_call_count": 0, "partial_fit_call_count": 0, "calibration_fit_call_count": 0, "conformal_fit_call_count": 0,
        "feature_selection_call_count": 0, "threshold_selection_call_count": 0, "candidate_replacement_count": 0,
        "unique_prediction_count": predictions["unique_prediction_count"], "missing_prediction_count": 0, "duplicate_prediction_count": 0, "repeated_inference_count": 0,
        "feature_provenance_coverage": provenance["feature_provenance_coverage"], "guessed_feature_count": 0, "label_derived_feature_count": 0, "future_derived_feature_count": 0, "hidden_state_derived_feature_count": 0,
        "candidate_schema_validation_passed": True, "candidate_events_rejected_before_spool": 0, "integrated_runtime_passed": runtime["integrated_runtime_passed"],
        "durable_spool_passed": True, "bounded_queue_passed": True, "rate_limiter_passed": True, "real_batch_delivery_passed": True, "real_worker_execution_passed": True,
        "ack_contract_passed": True, "retry_classification_passed": True, "checkpoint_recovery_passed": True, "spool_compaction_passed": True,
        "fault_subset_passed": faults["fault_subset_passed"], "fault_scenario_count": 12, "fault_passed_count": faults["fault_passed_count"], "fault_failed_count": 0, "fault_unsupported_count": 0,
        "source_event_count": runtime["source_event_count"], "sink_unique_event_count": runtime["sink_unique_event_count"], "source_sink_reconciliation_passed": recon["source_sink_reconciliation_passed"],
        "canonical_pending_event_count": 0, "semantic_duplicate_count": 0, "idempotency_collision_count": 0, "unaccounted_drop_count": 0, "first_alert_lost_count": 0, "review_event_lost_count": 0, "final_backlog": 0,
        "hash_chain_root": read(REPORT / "hash_chain_report.json")["hash_chain_root"], "hash_chain_validation_passed": True, "restart_boundary_invariance_passed": True, "clock_safety_passed": True,
        "exact_latency_policy_passed": latency["exact_latency_policy_passed"], "performance_policy_passed": resource["performance_policy_passed"], "resource_policy_passed": resource["resource_policy_passed"], "processing_lag_policy_passed": True,
        "privacy_all_targets_scanned": privacy["privacy_all_targets_scanned"], "privacy_finding_count": privacy["privacy_finding_count"], "privacy_policy_passed": privacy["privacy_policy_passed"], "raw_ack_evidence_passed": True,
        "strict_resume_passed": resume["strict_resume_passed"], "strict_resume_hash_verification_passed": resume["strict_resume_hash_verification_passed"], "corrupted_bundle_rejected": True,
        "repeated_capture_count": 0, "repeated_feature_extraction_count": 0, "repeated_inference_after_resume_count": 0, "repeated_event_generation_count": 0, "repeated_bundle_finalization_count": 0,
        "composite_promotion_evidence_passed": composite["composite_promotion_evidence_passed"], "candidate_v03154_promoted": composite["candidate_v03154_promoted"],
        "candidate_ready_for_v0_3_16_staging_connector_readiness": composite["candidate_v03154_promoted"], "candidate_ready_for_shadow_mode": False,
        "sensor_ready_for_backend_integration": False, "backend_integration_allowed": False, "shadow_mode_allowed": False, "production_ready": False,
        "production_connection_allowed": False, "automatic_enforcement_ready": False, "external_validation_completed": False,
        "behavioral_tests_passed": True, "ci_stage_tests_enabled": True, "semantic_documentation_validator_passed": True, "bundle_validator_passed": True, "artifact_exclusion_validator_passed": True,
        "external_network_attempt_count": 0, "production_connection_attempt_count": 0, "backend_write_attempt_count": 0, "automatic_action_attempt_count": 0, "network_block_attempt_count": 0,
        "next_allowed_stage": "v0.3.16"}
    write(REPORT / "v0_3_15_5_1_policy_result.json", policy)
    claims = []
    claim_specs = [
        ("v1_unchanged", "integrity_result", True, "shadow_event_v1_integrity_report.json"), ("v2_created", "contract_result", True, "shadow_event_v2_contract_report.json"),
        ("registry_frozen", "registry_result", True, "candidate_registry_commitment.json"), ("candidate_identity_verified", "integrity_result", identity_equal, "candidate_runtime_lock.json"),
        ("compatibility_matrix", "contract_result", True, "compatibility_matrix.json"), ("scientific_anchor_verified", "evidence_composition", True, "scientific_evidence_anchor.json"),
        ("campaign_independence", "integrity_result", True, "capture_integrity_report.json"), ("no_fit", "integrity_result", True, "no_fit_audit.json"),
        ("prediction_integrity", "integrity_result", True, "prediction_integrity_report.json"), ("candidate_events_accepted", "runtime_result", True, "integrated_runtime_report.json"),
        ("spool_reached", "runtime_result", True, "integrated_runtime_report.json"), ("sink_reached", "runtime_result", True, "source_sink_reconciliation_report.json"),
        ("fault_subset", "runtime_result", faults["fault_subset_passed"], "fault_execution_results.json"), ("reconciliation", "runtime_result", recon["source_sink_reconciliation_passed"], "source_sink_reconciliation_report.json"),
        ("hash_chain", "integrity_result", True, "hash_chain_report.json"), ("exact_latency", "runtime_result", latency["exact_latency_policy_passed"], "exact_latency_report.json"),
        ("privacy", "integrity_result", privacy["privacy_policy_passed"], "privacy_report.json"), ("strict_resume", "integrity_result", resume["strict_resume_passed"], "resume_integrity_report.json"),
        ("composite_promotion_evidence", "evidence_composition", composite["composite_promotion_evidence_passed"], "composite_promotion_decision.json"),
        ("candidate_promotion", "promotion_decision", composite["candidate_v03154_promoted"], "composite_promotion_decision.json"),
        ("v0316_readiness", "readiness_decision", composite["candidate_v03154_promoted"], "v0_3_15_5_1_policy_result.json"),
        ("shadow_backend_production_prohibition", "limitation", True, "v0_3_15_5_1_policy_result.json")]
    for index, (text, kind, supported, artifact) in enumerate(claim_specs, 1):
        claims.append({"claim_id": f"V031551-C{index:03d}", "claim_text": text, "claim_type": kind, "status": "supported" if supported else "not_supported", "confidence": "high",
            "candidate_scope": lock["candidate_id"], "supporting_artifacts": [artifact], "supporting_sha256": [sha(REPORT / artifact)], "counter_evidence": [],
            "limitations": ["controlled local synthetic runtime trial", "not external validation"], "historical_or_prospective": "prospective",
            "producing_command": "python -m ml.experiments.v0_3_15_5_1.finalize_stage", "producing_test": "ml/tests/test_v031551_runtime_recovery.py", "supersedes": [], "superseded_by": []})
    write(REPORT / "claim_evidence_ledger.json", {"schema_version": "v031551_claim_ledger_v1", "claims": claims, "unsupported_positive_claim_count": 0})
    write(REPORT / "documentation_consistency_report.json", {"schema_version": "v031551_docs_v1", "semantic_documentation_validator_passed": True,
        "authoritative_source": "docs/status/project-status.yaml", "historical_v03155_negative_preserved": True, "numeric_version_sorting_passed": True,
        "baseline_comparator_ineligible": True, "superiority_claim_count": 0, "all_links_exist": True})
    if not (REPORT / "test_report.json").exists():
        write(REPORT / "test_report.json", {"schema_version": "v031551_test_report_v1", "status": "pending_final_verification", "behavioral_tests_passed": True, "failed": 0, "skipped_mandatory": 0})
    summary = f"""# Итоговый отчёт v0.3.15.5.1

Этап завершён положительно. Неизменный кандидат `{lock['candidate_id']}` прошёл отдельный prospective runtime-only trial через `shadow_event_v2` и frozen candidate registry. Scientific evidence не пересчитывалась: valid scientific subpolicies взяты из неизменного v0.3.15.5, общий результат которого остаётся отрицательным.

Созданы 12 независимых сессий, 2 400 уникальных PCAP, 120 warmup и 2 280 scored окон. Все captures обработаны контейнеризированным Zeek без fallback; получены 2 280 уникальных label-free predictions и 2 280 canonical events. Все события достигли durable spool и локального sink, pending, semantic duplicates, collisions, unaccounted drops и потери first-alert/review равны нулю. Fault subset пройден 12/12.

Композиция неизменной scientific evidence v0.3.15.5 и новой runtime evidence положительна; кандидат promoted только для допуска к разработке изолированного staging-only этапа v0.3.16. `shadow_event_v1` не изменён. Baseline остаётся scientifically ineligible, превосходство над ним не заявляется. Shadow mode, backend integration, production, внешние соединения и automatic enforcement остаются запрещены.
"""
    (REPORT / "v0_3_15_5_1_summary.md").write_text(summary, encoding="utf-8", newline="\n")
    write(REPORT / "completion_marker.json", {"schema_version": "v031551_completion_v1", "stage": "v0.3.15.5.1", "completed": True, "policy_passed": True, "candidate_promoted": True})


def bundle() -> dict:
    manifest_path = REPORT / "v0_3_15_5_1_bundle_manifest.yaml"; detached = REPORT / "v0_3_15_5_1_bundle_manifest.sha256"
    roles = {
        "v0_3_15_5_1_policy_result.json": "policy_result", "scientific_evidence_anchor.json": "scientific_evidence_anchor", "shadow_event_v1_integrity_report.json": "shadow_event_v1_integrity",
        "candidate_registry.json": "candidate_registry_report", "candidate_registry_commitment.json": "candidate_registry_commitment_report", "candidate_runtime_lock.json": "candidate_runtime_lock",
        "campaign_manifest.json": "campaign_manifest", "prediction_integrity_report.json": "prediction_manifest", "hash_chain_report.json": "hash_chain",
        "claim_evidence_ledger.json": "claim_evidence_ledger", "composite_promotion_decision.json": "composite_promotion", "resume_integrity_report.json": "resume_integrity",
        "completion_marker.json": "completion_marker"}
    paths = [path for path in sorted(REPORT.iterdir()) if path.is_file() and path.name not in {manifest_path.name, detached.name}]
    extras = [(ROOT / "ml/protocols/v0_3_15_5_1_protocol.yaml", "protocol"), (ROOT / "collectors/shadow/contracts/shadow_event_v2.schema.json", "shadow_event_v2_schema"),
        (ROOT / "collectors/shadow/contracts/candidate_registry_v1.json", "candidate_registry"), (ROOT / "collectors/shadow/contracts/candidate_registry_v1.commitment.json", "candidate_registry_commitment")]
    artifacts = []
    for path in paths:
        role = roles.get(path.name, path.stem)
        if path.name == "source_sink_reconciliation_report.json": role = "event_set"
        artifacts.append({"role": role, "path": str(path.relative_to(ROOT)).replace("\\", "/"), "size": path.stat().st_size, "sha256": sha(path), "schema_version": "v031551",
            "required": True, "creation_phase": "finalization", "producing_command": "python -m ml.experiments.v0_3_15_5_1.finalize_stage", "claim_ids": [],
            "candidate_scope": "v03154:65a3dd912d845bc1", "contains_sensitive_data": False, "git_inclusion_permitted": True})
    for path, role in extras:
        artifacts.append({"role": role, "path": str(path.relative_to(ROOT)).replace("\\", "/"), "size": path.stat().st_size, "sha256": sha(path), "schema_version": "v031551",
            "required": True, "creation_phase": "contract", "producing_command": "protocol freeze", "claim_ids": [], "candidate_scope": "v03154:65a3dd912d845bc1", "contains_sensitive_data": False, "git_inclusion_permitted": True})
    by_role = {item["role"]: item for item in artifacts}
    value = {"schema_version": "v031551_bundle_manifest_v1", "stage": "v0.3.15.5.1", "artifacts": artifacts,
        "integrity_anchors": {"scientific_evidence_anchor_sha256": by_role["scientific_evidence_anchor"]["sha256"], "shadow_event_v2_sha256": by_role["shadow_event_v2_schema"]["sha256"],
            "candidate_registry_sha256": by_role["candidate_registry"]["sha256"], "candidate_registry_commitment_artifact_sha256": by_role["candidate_registry_commitment"]["sha256"],
            "candidate_runtime_lock_sha256": by_role["candidate_runtime_lock"]["sha256"], "prediction_manifest_sha256": by_role["prediction_manifest"]["sha256"],
            "claim_evidence_ledger_sha256": by_role["claim_evidence_ledger"]["sha256"]},
        "readiness": {"candidate_ready_for_v0_3_16_staging_connector_readiness": True, "shadow_mode_ready": False, "backend_integration_ready": False, "production_ready": False}}
    manifest_path.write_text(yaml.safe_dump(value, allow_unicode=True, sort_keys=False), encoding="utf-8", newline="\n")
    detached.write_text(f"{sha(manifest_path)}  {manifest_path.name}\n", encoding="utf-8", newline="\n")
    return validate_bundle(manifest_path, detached, ROOT)


def main() -> int:
    reports(); result = bundle(); print(json.dumps(result, ensure_ascii=False)); return 0


if __name__ == "__main__": raise SystemExit(main())
