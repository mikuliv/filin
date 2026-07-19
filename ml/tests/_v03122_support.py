from __future__ import annotations

import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
REPORT = ROOT / "ml/reports/v0_3_12_2"
EXPERIMENT = ROOT / "ml/experiments/v0_3_12_2"


def load(name: str):
    return json.loads((REPORT / name).read_text(encoding="utf-8"))


def load_yaml(name: str):
    return yaml.safe_load((EXPERIMENT / name).read_text(encoding="utf-8"))


def assert_contract(testcase, case: str):
    policy = load("v0_3_12_2_policy_result.json")
    if any(x in case for x in ("protocol_freeze", "registry_freeze")):
        freeze = load("protocol_freeze.json")
        testcase.assertTrue(freeze["v03122_protocol_frozen"])
        testcase.assertTrue(freeze["v03122_registry_frozen"])
    elif "coverage" in case:
        coverage = load("evaluation_coverage.json")
        testcase.assertEqual(coverage["scientific_denominator"], 3)
        testcase.assertTrue(coverage["scientific_coverage_policy_passed"])
        testcase.assertFalse(coverage["legacy_unavailable_affects_pass_fail"])
    elif "expected_counts" in case or "warmup" in case:
        lock = load("v038_input_lock.json")
        testcase.assertEqual((lock["scored_row_count"], lock["feature_count"]), (216, 51))
        testcase.assertEqual(len({row["run_id"] for row in lock["rows"]}), 6)
    elif "prediction_once" in case or "no_prediction" in case or "no_fit" in case:
        audit = load("no_fit_audit.json")
        testcase.assertTrue(audit["no_fit_audit_passed"])
        testcase.assertEqual(audit["v0.3.8_prediction_generation_count"], 1)
        testcase.assertEqual(audit["v0.3.9_prediction_generation_count"], 0)
        testcase.assertEqual(audit["v0.3.10_prediction_generation_count"], 0)
    elif "positive_causal_control" in case:
        short = "v039" if "v039" in case else "v0310"
        expected = {"1": 29, "2": 1, "3": 0, "4": 0} if short == "v039" else {"1": 60, "2": 0, "3": 0, "4": 0}
        testcase.assertEqual(load(f"{short}_metrics.json")["episode"]["alert_window_counts"], expected)
    elif "legacy_physical" in case:
        legacy = load("legacy_physical_order_control.json")
        testcase.assertEqual(legacy["v039"]["alert_counts"], {"1": 12, "2": 10, "3": 8})
        testcase.assertEqual(legacy["v0310"]["alert_counts"], {"1": 23, "2": 21, "3": 16})
        testcase.assertFalse(legacy["legacy_physical_order_metrics_affect_v03122_pass_fail"])
    elif "invariance" in case or "permutation" in case or "reverse_order" in case or "worker_order" in case:
        for short in ("v038", "v039", "v0310"):
            result = load(f"{short}_causal_invariance.json")
            testcase.assertTrue(result["causal_order_invariance_passed"])
            testcase.assertEqual(result["profile_count"], 6)
    elif "causal_sort" in case or "physical_order_fallback" in case:
        from ml.experiments.v0_3_12_2.causal_episode_evaluator import canonical_sort
        rows = [
            {"benchmark_id": "b", "run_id": "r", "activity_key": "a", "causal_order": 1, "immutable_row_id": "physical-first"},
            {"benchmark_id": "b", "run_id": "r", "activity_key": "a", "causal_order": 0, "immutable_row_id": "physical-second"},
        ]
        testcase.assertEqual(canonical_sort(rows)[0]["immutable_row_id"], "physical-second")
    elif "duplicate_causal_order" in case:
        from ml.experiments.v0_3_12_2.causal_episode_evaluator import canonical_sort
        row = {"benchmark_id": "b", "run_id": "r", "activity_key": "a", "causal_order": 0, "immutable_row_id": "x"}
        with testcase.assertRaises(ValueError):
            canonical_sort([row, {**row, "immutable_row_id": "y"}])
    elif "checkpoint_resume" in case:
        resume = load("resume_audit.json")
        testcase.assertTrue(resume["strict_resume_passed"])
        testcase.assertFalse(resume["v038_prediction_repeated"])
    elif "bundle_validation" in case:
        testcase.assertTrue(load("regression_bundle_validation.json")["all_valid"])
    elif "read_only" in case or "previous_stage" in case:
        testcase.assertTrue(load("read_only_access_audit.json")["historical_benchmarks_unchanged"])
    elif "readiness" in case or "policy_result" in case:
        testcase.assertTrue(policy["v03122_regression_completed"])
        testcase.assertTrue(policy["v03122_regression_passed"])
        testcase.assertTrue(policy["candidate_ready_for_v0_3_13_blind_holdout"])
        testcase.assertFalse(policy["candidate_ready_for_shadow_mode"])
        testcase.assertFalse(policy["sensor_ready_for_backend_integration"])
    elif "resource_monitor" in case:
        testcase.assertGreaterEqual(load("resource_summary.json")["sample_count"], 1)
    elif "summary" in case:
        text = (REPORT / "v0_3_12_2_summary.md").read_text(encoding="utf-8")
        testcase.assertIn("Филин v0.3.12.2", text)
        testcase.assertIn("Readiness for v0.3.13", text)
    else:
        testcase.assertTrue(policy["v03122_regression_completed"])
        testcase.assertTrue((REPORT / "combined_prediction_manifest.json").is_file())
