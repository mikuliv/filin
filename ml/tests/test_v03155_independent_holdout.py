from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

import pytest
import yaml

from collectors.shadow.schema_validator import validate as validate_event
from tools.audit.validate_v03155_artifacts import validate as validate_artifacts
from tools.audit.validate_v03155_bundle import validate as validate_bundle

ROOT = Path(__file__).resolve().parents[2]
CFG = ROOT / "ml/experiments/v0_3_15_5"
REPORT = ROOT / "ml/reports/v0_3_15_5"


def load(name): return json.loads((REPORT / name).read_text(encoding="utf-8"))
def yload(name): return yaml.safe_load((CFG / name).read_text(encoding="utf-8"))


def test_protocol_frozen_before_capture():
    p = yaml.safe_load((ROOT / "ml/protocols/v0_3_15_5_protocol.yaml").read_text(encoding="utf-8"))
    assert p["status"] == "frozen_before_first_capture" and p["revision"] == 1


def test_candidate_pair_integrity():
    pair = load("candidate_pair_lock.json")
    assert pair["candidate"]["candidate_id"] == "v03154:65a3dd912d845bc1"
    assert pair["candidate"]["artifact_sha256"] == "65a3dd912d845bc1d6e44247bb8b98fe228a7a4e0496d56a73857febbaa4df87"


def test_baseline_eligibility_gate():
    value = load("baseline_comparator_eligibility_report.json")
    assert not value["baseline_comparator_eligible"] and value["uses_generator_profile"] and value["uses_hidden_state"]


def test_baseline_hidden_metadata_prohibited(): assert load("baseline_prediction_manifest.json")["prediction_count"] == 0


def test_independence_validator(): assert load("independence_validation_report.json")["independence_validation_passed"]


def test_seed_and_session_overlap_detection():
    value = load("independence_validation_report.json")
    assert value["seed_overlap_count"] == value["session_overlap_count"] == 0


def test_parameter_overlap_detection(): assert load("independence_validation_report.json")["exact_parameter_overlap_count"] == 0


@pytest.mark.parametrize("group", ["balanced", "auth_generalization", "web_probe_generalization", "background_shift", "runtime_resilience"])
def test_session_groups(group):
    sessions = yload("campaign.yaml")["sessions"]
    assert sum(row["session_group"] == group for row in sessions) == 4


@pytest.mark.parametrize("attack", ["auth_failures", "beacon", "low_rate_dos", "port_scan", "web_probe"])
def test_attack_episode_balance(attack):
    rows = [r for r in yload("episode_schedule.yaml")["episodes"] if r["class"] == attack]
    assert len(rows) == 20 and Counter(r["length"] for r in rows) == {2: 5, 3: 5, 4: 5, 5: 5}


def test_benign_variant_independence():
    grouped = defaultdict(list)
    for row in yload("episode_schedule.yaml")["episodes"]:
        if row["benign_variant_id"]: grouped[row["benign_variant_id"]].append(row)
    assert len(grouped) == 50 and all(len(v) == 2 and v[0]["session_group"] != v[1]["session_group"] for v in grouped.values())


def test_auth_holdout_contract(): assert load("candidate_per_class_metrics.json")["classes"]["auth_failures"]["recall"] == 1.0
def test_web_probe_holdout_contract(): assert load("candidate_per_class_metrics.json")["classes"]["web_probe"]["recall"] == 1.0
def test_feature_path_isolation(): assert load("feature_path_isolation_report.json")["feature_path_isolation_passed"]
def test_provenance_completeness(): assert load("feature_v2_provenance_report.json")["provenance_record_count"] == 193800
def test_label_vault_separation(): assert load("pre_label_trial_lock.json")["created_before_label_unlock"]
def test_no_fit_audit(): assert load("no_fit_audit.json")["no_fit_audit_passed"]
def test_prediction_uniqueness(): assert load("candidate_prediction_manifest.json")["unique_prediction_count"] == 3800
def test_candidate_namespace_isolation(): assert load("candidate_stateful_metrics.json")["cross_candidate_contamination"] == 0
def test_cross_candidate_contamination(): assert load("candidate_stateful_metrics.json")["cross_candidate_contamination"] == 0
def test_paired_comparison_correctness(): assert load("paired_window_comparison.json")["status"] == "not_applicable_baseline_ineligible"
def test_session_bootstrap(): assert load("bootstrap_intervals.json")["iterations"] == 5000
def test_comparative_noninferiority_na(): assert load("comparative_noninferiority_report.json")["passed"] is None
def test_conformal_gates(): assert load("conformal_metrics.json")["candidate_conformal_policy_passed"]
def test_runtime_fault_subset_fails_closed(): assert load("fault_execution_results.json")["fault_failed_count"] == 12
def test_raw_ack_evidence(): assert load("raw_ack_evidence_report.json")["raw_ack_evidence_passed"]
def test_exact_latency_fails_closed(): assert not load("exact_latency_report.json")["exact_latency_policy_passed"]
def test_cpu_normalization(): assert load("resource_report.json")["logical_cpu_count"] >= 1
def test_source_sink_reconciliation_detects_failure(): assert load("source_sink_reconciliation_report.json")["unaccounted_drop_count"] == 3800
def test_strict_resume(): assert load("resume_integrity_report.json")["strict_resume_passed"]
def test_corruption_rejection(): assert load("resume_integrity_report.json")["corruption_rejected_count"] == 11
def test_promotion_policy(): assert not load("promotion_decision.json")["candidate_v03154_promoted"]
def test_readiness_consistency(): assert not load("v0_3_15_5_policy_result.json")["candidate_ready_for_v0_3_16_staging_connector_readiness"]
def test_artifact_validation(): assert validate_artifacts()["artifact_exclusion_validator_passed"]


def test_candidate_event_contract_mismatch_is_behavioral():
    error = load("runtime_configuration_report.json")["candidate_event_schema_error"]
    assert "v0311:19176acb401be2d4" in error


def test_bundle_validation():
    result = validate_bundle(REPORT / "v0_3_15_5_bundle_manifest.yaml", REPORT / "v0_3_15_5_bundle_manifest.sha256", ROOT)
    assert result["bundle_validator_passed"], result["errors"]


@pytest.mark.parametrize("name", [
    "historical_integrity_report.json", "protocol_lock.json", "candidate_pair_lock.json", "independence_manifest.json",
    "campaign_manifest.json", "session_manifest.json", "episode_schedule_manifest.json", "scenario_variant_manifest.json",
    "benign_variant_manifest.json", "label_vault_commitment.json", "capture_integrity_report.json",
    "feature_v2_provenance_report.json", "candidate_prediction_manifest.json", "pre_label_trial_lock.json",
    "candidate_window_metrics.json", "candidate_episode_metrics.json", "candidate_stateful_metrics.json",
    "calibration_metrics.json", "conformal_metrics.json", "bootstrap_intervals.json", "drift_report.json",
    "runtime_configuration_report.json", "fault_execution_results.json", "source_sink_reconciliation_report.json",
    "exact_latency_report.json", "resource_report.json", "raw_ack_evidence_report.json", "privacy_report.json",
    "resume_integrity_report.json", "promotion_decision.json", "claim_evidence_ledger.json",
])
def test_required_report_exists(name): assert (REPORT / name).is_file()


def test_historical_hash_preservation(): assert load("historical_integrity_report.json")["historical_stages_unchanged"]
def test_backend_unchanged(): assert load("historical_integrity_report.json")["backend_tree_unchanged"]
def test_privacy_policy(): assert load("privacy_report.json")["privacy_finding_count"] == 0
def test_external_attempts_zero(): assert load("v0_3_15_5_policy_result.json")["external_network_attempt_count"] == 0
