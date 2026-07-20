from __future__ import annotations

import json
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
CFG = ROOT / "ml/experiments/v0_3_15"
REPORT = ROOT / "ml/reports/v0_3_15"


def load_json(name: str) -> dict:
    return json.loads((REPORT / name).read_text(encoding="utf-8"))


def verify_case(case: unittest.TestCase, stem: str) -> None:
    policy = load_json("v0_3_15_policy_result.json")
    case.assertTrue(policy["v0315_controlled_shadow_completed"])
    cases = {
        "protocol_freeze": "v0315_protocol_frozen", "candidate_integrity": "candidate_integrity_passed", "previous_stage_integrity": "previous_stages_unchanged",
        "safety_policy": "safety_policy_passed", "condition_independence": "condition_independence_passed", "capture_lock": "capture_lock_passed",
        "feature_schema": "feature_integrity_passed", "causal_features": "feature_integrity_passed", "row_identity": "unique_prediction_integrity_passed", "activity_key": "feature_integrity_passed",
        "blind_label_guard": "blind_label_separation_passed", "blind_access": "blind_access_audit_passed", "no_fit": "no_fit_audit_passed", "unique_prediction": "unique_prediction_integrity_passed",
        "prediction_before_label_unlock": "prediction_before_label_unlock_passed", "prediction_resume": "checkpoint_resume_passed", "event_contract_integrity": "event_contract_integrity_passed",
        "source_event_reconciliation": "source_event_reconciliation_passed", "sink_event_reconciliation": "sink_event_reconciliation_passed", "permutation_invariance": "causal_order_invariance_passed",
        "restart_boundary_invariance": "causal_order_invariance_passed", "window_metrics": "window_policy_passed", "stateful_metrics": "stateful_policy_passed", "episode_metrics": "episode_policy_passed",
        "per_class_metrics": "per_class_policy_passed", "per_session_metrics": "per_session_policy_passed", "per_group_metrics": "per_group_policy_passed", "per_variant_metrics": "all_benign_variant_policies_passed",
        "per_length_metrics": "episode_length_policy_passed", "continuous_availability": "continuous_availability_policy_passed", "processing_latency": "processing_latency_policy_passed", "processing_lag": "processing_lag_policy_passed",
        "sink_fault_isolation": "transport_fault_isolation_passed", "state_recovery": "restart_recovery_policy_passed", "spool_recovery": "restart_recovery_policy_passed", "privacy": "privacy_policy_passed",
        "fail_safe": "fail_safe_policy_passed", "no_backend_write": "no_production_connection_passed", "no_external_connection": "no_production_connection_passed", "calibration": "calibration_policy_passed",
        "conformal": "conformal_policy_passed", "bootstrap": "bootstrap_completed", "bundle_pre_manifest": "shadow_trial_bundle_completed", "bundle_completion": "shadow_trial_bundle_completed",
        "bundle_validation": "shadow_trial_bundle_validated", "resource_limits": "resource_policy_passed", "checkpoint_resume": "checkpoint_resume_passed", "policy_result": "v0315_controlled_shadow_passed",
    }
    suffix = stem.removeprefix("test_v0315_")
    if suffix in cases: case.assertTrue(policy[cases[suffix]], suffix)
    if suffix in {"campaign_counts", "attack_class_balance", "benign_variant_balance", "episode_length_balance", "schedule_freeze", "seed_uniqueness"}:
        campaign = load_json("campaign_integrity.json"); case.assertEqual(campaign["session_count"], 10); case.assertTrue(campaign["attack_class_balance_passed"]); case.assertTrue(campaign["benign_variant_balance_passed"])
    if suffix in {"capture_counts", "capture_hashes", "no_fallback"}:
        capture = load_json("capture_manifest.json"); case.assertEqual(capture["capture_count"], 1520); case.assertEqual(capture["unique_capture_count"], 1520); case.assertEqual(capture["fallback_count"], 0)
    if suffix in {"online_window_processing", "stage_runner"}:
        case.assertEqual(policy["unique_prediction_row_count"], 1440); case.assertEqual(policy["missing_prediction_row_count"], 0)
    if suffix in {"state_persistence", "exporter_restart", "sensor_restart", "first_alert_not_lost", "review_not_lost"}:
        recovery = load_json("restart_recovery.json"); case.assertTrue(recovery["restart_recovery_policy_passed"]); case.assertEqual(recovery["first_alert_lost_count"], 0); case.assertEqual(recovery["review_event_lost_count"], 0)
    if suffix in {"idempotency", "hash_chain"}:
        sink = load_json("sink_event_reconciliation.json"); case.assertTrue(sink["sink_event_reconciliation_passed"])
    if suffix in {"causal_sort", "no_physical_order_fallback"}:
        case.assertTrue(load_json("causal_order_invariance.json")["causal_order_invariance_passed"])
    if suffix == "summary": case.assertIn("## Conclusion", (REPORT / "v0_3_15_summary.md").read_text(encoding="utf-8"))
