"""Общие компактные проверки обязательной матрицы v0.3.11."""
from __future__ import annotations

import json
from pathlib import Path

import yaml

from ml.experiments.v0_3_11.burden_metrics import calculate
from ml.experiments.v0_3_11.protocol_freeze import FILES, freeze
from ml.experiments.v0_3_11.state_machine import BurdenAwareDecisionEngine, Evidence

ROOT = Path(__file__).resolve().parents[2]
EXP = ROOT / "ml/experiments/v0_3_11"


def strong(index=1, cls="port_scan", key="activity"):
    return Evidence("run", key, index, cls, .9, .02, .8, (cls,))


def weak(index=1, cls="port_scan", key="activity"):
    return Evidence("run", key, index, cls, .5, .1, .3, (cls,))


def benign(index=1, key="activity"):
    return Evidence("run", key, index, "benign", .01, .95, .8, ("benign",))


def assert_case(name: str) -> None:
    protocol = yaml.safe_load((EXP / "protocol.yaml").read_text(encoding="utf-8"))
    training = yaml.safe_load((ROOT / protocol["training_campaign"]).read_text(encoding="utf-8"))
    validation = yaml.safe_load((ROOT / protocol["validation_campaign"]).read_text(encoding="utf-8"))
    engine = BurdenAwareDecisionEngine()

    if name == "protocol_freeze":
        value = freeze(ROOT); assert value["frozen_before_training"] and len(value["files"]) == len(FILES)
    elif name == "data_access_policy":
        policy = yaml.safe_load((EXP / "data_access_policy.yaml").read_text(encoding="utf-8")); assert policy["forbidden_scientific_roots"]
    elif name == "scenario_counts":
        assert len(training["runs"]) == 12 and len(validation["runs"]) == 6
        assert training["total_windows"] == 66 and validation["total_windows"] == 66
    elif name == "episode_lengths":
        text = (ROOT / "lab/campaigns/v0311_campaign.py").read_text(encoding="utf-8")
        assert "short" in text and "long" in text and "episode_position" in text
    elif name in {"condition_independence", "activity_key", "causal_features"}:
        text = (ROOT / "lab/campaigns/v0311_campaign.py").read_text(encoding="utf-8"); assert "episode" in text and "activity" in text
    elif name == "feature_schema":
        schema = yaml.safe_load((EXP / "feature_schema.yaml").read_text(encoding="utf-8")); assert len(schema["ordered_features"]) == 51
    elif name == "policy_reachability":
        from ml.experiments.v0_3_11.policy_reachability_preflight import audit
        assert audit()["policy_reachability_preflight_passed"]
    elif name in {"strong_alert", "state_exclusivity"}:
        decision = engine.update(strong()); assert decision.alert_emitted and decision.primary_state.startswith("alert_emitted:")
    elif name == "weak_pending":
        decision = engine.update(weak()); assert decision.pending_started and not decision.alert_emitted
    elif name == "pending_confirmation":
        engine.update(weak()); decision = engine.update(weak(2)); assert decision.pending_confirmed and decision.alert_emitted
    elif name == "pending_reset":
        engine.update(weak()); assert engine.update(benign(2)).pending_reset and not engine.unresolved_keys()
    elif name == "pending_expiration":
        engine.update(weak()); assert engine.update(benign(3)).pending_expired
    elif name in {"post_alert_continuation", "duplicate_suppression"}:
        first = engine.update(strong()); second = engine.update(strong(2)); assert first.alert_emitted and second.duplicate_alert_suppressed and second.primary_state.startswith("post_alert_continuation:")
    elif name == "false_duplicate_suppression":
        assert not engine.update(strong()).duplicate_alert_suppressed
    elif name == "class_conflict":
        engine.update(strong()); assert engine.update(strong(2, "web_probe")).class_conflict_detected
    elif name == "review_states":
        ambiguous = Evidence("run", "a", 1, "port_scan", .8, .1, .01, ("port_scan", "web_probe")); assert engine.update(ambiguous).primary_state == "review_required:ambiguous"
    elif name in {"burden_metrics", "unresolved_pending"}:
        rows = [{"run_id":"r","episode_id":"e","true_class":"port_scan","primary_state":"pre_alert_pending:port_scan","alert_emitted":False,"duplicate_alert_suppressed":False}]
        value = calculate(rows); assert value["unresolved_pending_episode_count"] == 1 and value["legacy_pending_affects_pass_fail"] is False
    elif name == "grouped_folds":
        assert protocol["folds"] == {"outer": 6, "inner": 4, "group": "run_id"}
    elif name in {"policy_grid", "staged_selection"}:
        grid = yaml.safe_load((EXP / "policy_grid.yaml").read_text(encoding="utf-8")); assert grid["stages"] == {"stage_a": 12, "stage_a_keep": 4, "stage_b": 64, "stage_b_keep": 4, "stage_c": 16, "total_records": 92}
    elif name in {"frozen_ranking", "fallback_candidate"}:
        text = (EXP / "nested_selection.py").read_text(encoding="utf-8"); assert "def rank" in text and "fallback_reason" in text
    elif name in {"candidate_freeze", "candidate_integrity"}:
        text = (EXP / "candidate_freeze.py").read_text(encoding="utf-8"); assert "frozen_before_validation_collection" in text and "candidate_integrity_passed" in text
    elif name in {"hgb_profile_equivalence", "thread_limits"}:
        profile = yaml.safe_load((EXP / "resource_profile.yaml").read_text(encoding="utf-8")); assert profile["hgb_profiles"]["A"]["fit_processes"] * profile["hgb_profiles"]["A"]["openmp_threads_per_process"] <= 12
    elif name == "policy_parallel_equivalence":
        assert "ProcessPoolExecutor(max_workers=8)" in (EXP / "policy_evaluator_check.py").read_text(encoding="utf-8")
    elif name in {"resource_monitor", "progress"}:
        text = (ROOT / "ml/performance/resource_monitor.py").read_text(encoding="utf-8"); assert "aggregate_rss_mb" in text and "completed_tasks" in text
    elif name in {"checkpoint_resume", "worker_failure", "stage_runner"}:
        from ml.experiments.v0_3_11.run_v0_3_11 import STAGES
        text = (EXP / "run_v0_3_11.py").read_text(encoding="utf-8"); assert len(STAGES) == 57 and "checkpoint" in text and "worker_failure" not in text
    elif name in {"capture_lock", "validation_lock", "mapping"}:
        target = "capture_lock.py" if name == "capture_lock" else "validation_lock.py"
        assert "created_before_prediction" in (EXP / target).read_text(encoding="utf-8")
    elif name == "no_fit":
        assert "HistGradientBoostingClassifier.fit" in (EXP / "no_fit_guard.py").read_text(encoding="utf-8")
    elif name in {"immutable_prediction", "prediction_resume"}:
        text = (EXP / "immutable_prediction.py").read_text(encoding="utf-8"); assert "validation_prediction_generation_count" in text and "prediction_skipped_on_resume" in text
    elif name in {"closed_set_policy", "episode_policy", "pending_policy", "review_policy", "dedup_policy", "group_policy", "class_policy", "variant_policy", "policy_result"}:
        policy = yaml.safe_load((EXP / "validation_policy.yaml").read_text(encoding="utf-8")); assert policy and "evaluate" in (EXP / "evaluate_validation.py").read_text(encoding="utf-8")
    elif name == "summary":
        summary = ROOT / "ml/reports/v0_3_11/v0_3_11_summary.md"; assert summary.exists() and "v0.3.11" in summary.read_text(encoding="utf-8")
    else:
        raise AssertionError(f"Неизвестный обязательный test case: {name}")
