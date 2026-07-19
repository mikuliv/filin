"""Общие фактические проверки frozen-артефактов v0.3.13."""
from __future__ import annotations

import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
REPORT = ROOT / "ml/reports/v0_3_13"
CFG = ROOT / "ml/experiments/v0_3_13"


def load(name):
    path = REPORT / name
    assert path.is_file() and path.stat().st_size > 0, path
    return json.loads(path.read_text(encoding="utf-8"))


def check(slug: str):
    policy = load("v0_3_13_policy_result.json")
    campaign = load("campaign_integrity.json")
    assert policy["v0313_holdout_completed"] is True
    if any(word in slug for word in ("campaign", "seed", "episode_balance", "attack_class", "benign_variant", "episode_lengths", "condition", "environment")):
        assert (campaign["run_count"], campaign["marker_count"], campaign["scored_rows"], campaign["warmup_rows"], campaign["episode_count"]) == (10, 760, 700, 60, 200)
        assert len(set(campaign["seeds"])) == 10
        assert campaign["benign_episode_count"] == campaign["attack_episode_count"] == 100
    if "capture" in slug or "sensor_fallback" in slug:
        capture = load("capture_lock.json")
        assert capture["capture_count"] == capture["capture_hash_count"] == 760
        assert capture["duplicate_capture_hash_count"] == capture["missing_capture_count"] == capture["fallback_path_count"] == 0
    if any(word in slug for word in ("feature", "row_identity", "activity_key", "episode_structure", "input_lock")):
        feature = load("feature_integrity.json")
        assert feature["feature_count"] == 51 and feature["scored_row_count"] == 700
        assert feature["label_leakage_count"] == feature["future_leakage_count"] == 0
    if any(word in slug for word in ("blind", "no_fit", "prediction")):
        access = load("blind_access_audit.json")
        nofit = load("no_fit_audit.json")
        prediction = load("immutable_prediction_manifest.json")
        assert access["blind_access_audit_passed"] and nofit["no_fit_audit_passed"]
        assert prediction["record_count"] == 700 and prediction["true_labels_included"] is False
        assert nofit["prediction_generation_count"] == 1
    if "invariance" in slug or "order" in slug or "causal_sort" in slug:
        value = load("causal_order_invariance.json")
        assert value["causal_order_invariance_passed"] and value["profile_count"] == 7
        assert len(set(value["profile_hashes"].values())) == 1
    if "metrics" in slug or "controls" in slug:
        window = load("window_metrics.json")
        episode = load("episode_metrics.json")
        assert window["row_count"] == 700 and window["macro_f1"] >= .90
        assert episode["episode_count"] == 200 and episode["attack_episode_recall"] >= .90
    if "bootstrap" in slug:
        assert load("bootstrap_intervals.json")["iterations"] == 5000
    if "bundle" in slug:
        assert load("regression_bundle_validation.json")["valid"] is True
        assert (REPORT / "regression_bundle_manifest.yaml").is_file()
    if "performance" in slug or "resource" in slug:
        assert load("stage_timings.json")["prediction_wall_seconds"] <= 120
        assert (REPORT / "resource_summary.json").is_file()
    if "summary" in slug:
        text = (REPORT / "v0_3_13_summary.md").read_text(encoding="utf-8")
        assert "v0.3.13" in text and "## Conclusion" in text
    if "protocol" in slug:
        frozen = load("protocol_freeze.json")
        assert frozen["v0313_protocol_frozen"] and len(frozen["hashes"]["protocol"]) == 64
    if "previous_stage" in slug or "candidate_integrity" in slug:
        previous = load("previous_stage_integrity.json")
        assert previous["v03122_positive_control_passed"] and previous["mismatches"] == {}
    if "readiness" in slug or "policy" in slug or "catastrophic" in slug:
        assert policy["v0313_holdout_passed"] is True
        assert policy["candidate_ready_for_v0_3_14_shadow_readiness"] is True
        assert policy["candidate_ready_for_shadow_mode"] is False and policy["sensor_ready_for_backend_integration"] is False
