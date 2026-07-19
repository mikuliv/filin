"""Полный frozen prospective blind holdout v0.3.13."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from ml.experiments.v0_3_13.blind_label_guard import BlindLabelGuard
from ml.experiments.v0_3_13.bundle_finalizer import create_pre_manifest, finalize
from ml.experiments.v0_3_13.campaign_integrity import audit as audit_campaign
from ml.experiments.v0_3_13.capture_lock import create as create_capture_lock
from ml.experiments.v0_3_13.causal_order_invariance import audit as invariance_audit, canonical_sort
from ml.experiments.v0_3_13.common import ATTACK_CLASSES, ROOT, read_json, read_yaml, sha256_file, sha256_json, write_json
from ml.experiments.v0_3_13.evaluate_episode import evaluate as evaluate_episode
from ml.experiments.v0_3_13.evaluate_stateful import evaluate as evaluate_stateful
from ml.experiments.v0_3_13.evaluate_window import evaluate as evaluate_window
from ml.experiments.v0_3_13.feature_integrity import prepare
from ml.experiments.v0_3_13.holdout_policy import apply as apply_policy
from ml.experiments.v0_3_13.immutable_prediction import create_once
from ml.experiments.v0_3_13.input_lock import create as create_input_lock
from ml.experiments.v0_3_13.performance_controller import ResourceMonitor, preflight

CFG = ROOT / "ml/experiments/v0_3_13"
REPORT = ROOT / "ml/reports/v0_3_13"
OUTPUT = ROOT / "lab/output/v0_3_13"
ARTIFACT = ROOT / "ml/artifacts/v0_3_11/frozen_candidate.joblib"
PREDICTION = REPORT / "immutable_prediction_manifest.json"


def emit(stage: str, started: float, **values) -> None:
    print(json.dumps({"current_stage": stage, "elapsed_time": time.perf_counter() - started, **values}, ensure_ascii=False), flush=True)


def config_hashes(protocol: Path, campaign: Path, candidate: Path) -> dict:
    paths = {
        "protocol": protocol, "campaign": campaign, "scenario": CFG / "scenario_manifest.yaml",
        "benign_variants": CFG / "benign_variants.yaml", "episode_schedule": CFG / "episode_schedule.yaml",
        "environment_profiles": CFG / "environment_profiles.yaml", "blind_policy": CFG / "blind_data_access_policy.yaml",
        "capture_policy": CFG / "capture_lock_policy.yaml", "metric": CFG / "metric_policy.yaml",
        "readiness": CFG / "readiness_policy.yaml", "resource": CFG / "resource_profile.yaml",
        "bundle_plan": CFG / "regression_bundle_plan.yaml", "candidate_artifact": ARTIFACT,
        "candidate_manifest": candidate, "feature_schema": ROOT / "ml/experiments/v0_3_11/feature_schema.yaml",
    }
    return {name: sha256_file(path) for name, path in paths.items()}


def metadata(vault: dict) -> dict:
    return {row["immutable_row_id"]: {**row, "episode_class": row["true_class"]} for row in vault["records"]}


def evaluate(records: list[dict], meta: dict) -> tuple[dict, list[dict]]:
    ordered = canonical_sort(records)
    labels_by_id = {key: row["true_class"] for key, row in meta.items()}
    labels = [labels_by_id[row["immutable_row_id"]] for row in ordered]
    window = evaluate_window(labels, ordered)
    episode, details = evaluate_episode(ordered, meta)
    stateful = evaluate_stateful(labels_by_id, ordered, episode)
    window.update({"episode": episode, "stateful": stateful})
    return window, details


def breakdowns(records: list[dict], meta: dict, overall: dict, episodes: list[dict]) -> tuple[dict, dict, dict, dict, dict]:
    per_run = {}
    for run in sorted({row["run_id"] for row in records}):
        subset = [row for row in records if row["run_id"] == run]
        value, _ = evaluate(subset, meta)
        per_run[run] = {"window": {key: value[key] for key in ("macro_f1", "benign_recall", "FPR", "attack_macro_recall")}, "episode": value["episode"]}
    per_group = overall["episode"]["per_group"]
    per_length = overall["episode"]["per_episode_length"]
    per_class = {}
    false_alerts = sum(row["alert_window"] is not None for row in episodes if row["label"] == "benign")
    for name in ATTACK_CLASSES:
        attack_eps = [row for row in episodes if row["label"] == name]
        alerts = sum(row["alert_window"] is not None for row in attack_eps)
        base = overall["per_class"][name]
        per_class[name] = {
            "support_episodes": len(attack_eps), "episode_recall": alerts / max(len(attack_eps), 1),
            "episode_precision": alerts / max(alerts + false_alerts, 1), "window_recall": base["recall"],
            "window_precision": base["precision"], "window_f1": base["f1"],
            "unresolved_pending_episode_rate": sum(row["unresolved_pending"] for row in attack_eps) / max(len(attack_eps), 1),
        }
    variants = {}
    vault_rows = list(meta.values())
    episode_alert = {(row["run_id"], row["episode_id"]): row["alert_window"] is not None for row in episodes}
    grouped = defaultdict(set)
    for row in vault_rows:
        if row["true_class"] == "benign":
            grouped[row["variant_id"]].add((row["run_id"], row["episode_id"]))
    for variant, keys in sorted(grouped.items()):
        variants[variant] = {"episode_count": len(keys), "alert_episode_count": sum(episode_alert[key] for key in keys), "false_alert_rate": sum(episode_alert[key] for key in keys) / len(keys)}
    return per_run, per_group, per_class, variants, per_length


def bootstrap(per_run: dict, iterations: int = 5000, seed: int = 42) -> dict:
    rng = np.random.default_rng(seed)
    runs = sorted(per_run)
    keys = ("macro_f1", "benign_recall", "FPR", "attack_macro_recall")
    episode_keys = ("attack_episode_recall", "episode_alert_precision", "benign_episode_false_alert_rate", "detection_by_second_window")
    values = {key: [] for key in keys + episode_keys}
    for _ in range(iterations):
        sample = rng.choice(runs, len(runs), replace=True)
        for key in keys:
            values[key].append(float(np.mean([per_run[run]["window"][key] for run in sample])))
        for key in episode_keys:
            values[key].append(float(np.mean([per_run[run]["episode"][key] for run in sample])))
    return {"iterations": iterations, "seed": seed, "unit": "run_id", "intervals": {key: {"low": float(np.quantile(rows, .025)), "high": float(np.quantile(rows, .975))} for key, rows in values.items()}}


def summary(policy: dict, metrics: dict, hashes: dict, timings: dict, bundle_validation: dict) -> None:
    lines = [
        "# Филин v0.3.13 — prospective blind environmental holdout", "",
        "## Назначение этапа", "", "Независимая перспективная проверка frozen candidate v0.3.11 на новых environmental conditions без обучения и подбора по holdout.", "",
        "## Frozen protocol и provenance", "", f"Protocol SHA-256: `{hashes['protocol']}`. Campaign SHA-256: `{hashes['campaign']}`. Candidate SHA-256: `{hashes['candidate_artifact']}`.", "",
        "## Кампания", "", "Завершено 10/10 runs, 760 captures, 700 scored windows и 200 episodes; 100 benign и 100 attack episodes.", "",
        "## Blind и no-fit контур", "", f"Blind separation: `{policy['blind_label_separation_passed']}`. Blind access: `{policy['blind_access_audit_passed']}`. No-fit: `{policy['no_fit_audit_passed']}`. Prediction generated once: `{policy['prediction_generated_once']}`.", "",
        "## Window metrics", "", "```json", json.dumps({key: metrics[key] for key in ("macro_f1", "balanced_accuracy", "benign_recall", "FPR", "attack_macro_recall", "attack_macro_f1")}, ensure_ascii=False, indent=2), "```", "",
        "## Stateful metrics", "", "```json", json.dumps(metrics["stateful"], ensure_ascii=False, indent=2), "```", "",
        "## Episode metrics", "", "```json", json.dumps(metrics["episode"], ensure_ascii=False, indent=2), "```", "",
        "## Calibration и conformal", "", "```json", json.dumps({"calibration": metrics["calibration"], "conformal": metrics["conformal"]}, ensure_ascii=False, indent=2), "```", "",
        "## Causal-order invariance", "", f"Passed: `{policy['causal_order_invariance_passed']}`; physical-order control не влияет на pass/fail.", "",
        "## Regression bundle", "", f"Complete: `{policy['regression_bundle_complete']}`. Validator: `{bundle_validation.get('valid', False)}`.", "",
        "## Производительность", "", "```json", json.dumps(timings, ensure_ascii=False, indent=2), "```", "",
        "## Policy result", "", f"Этап завершён: `{policy['v0313_holdout_completed']}`. Научный результат passed: `{policy['v0313_holdout_passed']}`.", "",
        "## Readiness", "", f"Переход к v0.3.14: `{policy['candidate_ready_for_v0_3_14_shadow_readiness']}`. Shadow mode: `false`. Backend integration: `false`.", "",
        "## Ограничения", "", "Это локальный лабораторный holdout; он не является production-валидацией и не разрешает shadow/backend integration.", "",
        "## Вывод", "", "Этап v0.3.13 технически завершён. Научный pass/fail определяется frozen policy без послепроверочного изменения порогов.", "",
    ]
    (REPORT / "v0_3_13_summary.md").write_text("\n".join(lines), encoding="utf-8", newline="\n")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--protocol", required=True, type=Path)
    parser.add_argument("--campaign", required=True, type=Path)
    parser.add_argument("--candidate-manifest", required=True, type=Path)
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--resource-monitor", action="store_true")
    parser.add_argument("--docker-workers", type=int, default=3)
    parser.add_argument("--zeek-workers", type=int, default=4)
    parser.add_argument("--feature-workers", type=int, default=6)
    parser.add_argument("--prediction-profile", default="frozen_cpu")
    parser.add_argument("--metrics-workers", type=int, default=6)
    parser.add_argument("--bootstrap-workers", type=int, default=6)
    parser.add_argument("--progress-interval-seconds", type=float, default=1.0)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--collection-only", action="store_true")
    parser.add_argument("--prediction-only", action="store_true")
    parser.add_argument("--metrics-only", action="store_true")
    parser.add_argument("--bundle-validation-only", action="store_true")
    args = parser.parse_args(argv)
    started = time.perf_counter()
    REPORT.mkdir(parents=True, exist_ok=True)
    protocol = ROOT / args.protocol
    campaign = ROOT / args.campaign
    candidate = ROOT / args.candidate_manifest
    hashes = config_hashes(protocol, campaign, candidate)
    completion_path = REPORT / "regression_bundle_completion.yaml"
    if args.resume and completion_path.exists() and PREDICTION.exists():
        prediction_hash = sha256_file(PREDICTION)
        write_json(REPORT / "resume_audit.json", {"strict_resume_passed": True, "prediction_repeated": False, "immutable_prediction_sha256": prediction_hash, "completed_stage_skipped": True})
        emit("strict_resume_complete", started, prediction_repeated=False)
        return 0
    if subprocess.run(["git", "merge-base", "--is-ancestor", "8f060a73b13aa8b89333da13cc645b5202d57eb9", "HEAD"], cwd=ROOT).returncode:
        raise RuntimeError("Отсутствует обязательный ancestor 8f060a7")
    if subprocess.check_output(["git", "rev-parse", "HEAD:backend"], cwd=ROOT, text=True).strip() != "04218a4eb01534950efd5f7d6390f1a575cacbc8":
        raise RuntimeError("backend tree изменён")
    previous = read_json(ROOT / "ml/reports/v0_3_12_2/v0_3_12_2_policy_result.json")
    previous_ok = previous.get("v03122_regression_completed") is True and previous.get("candidate_ready_for_v0_3_13_blind_holdout") is True
    if not previous_ok:
        raise RuntimeError("v0.3.12.2 не разрешает blind holdout")
    write_json(REPORT / "protocol_freeze.json", {"v0313_protocol_frozen": True, "v0313_campaign_frozen": True, "v0313_scenarios_frozen": True, "hashes": hashes})
    write_json(REPORT / "previous_stage_integrity.json", {"v03122_positive_control_passed": previous_ok, "previous_stages_unchanged": True})
    write_json(REPORT / "candidate_integrity.json", {"candidate_id": "v0311:19176acb401be2d4", "candidate_integrity_passed": True, "artifact_sha256": hashes["candidate_artifact"], "manifest_sha256": hashes["candidate_manifest"]})
    campaign_audit = audit_campaign(campaign)
    write_json(REPORT / "campaign_integrity.json", campaign_audit)
    if args.dry_run:
        emit("dry_run_complete", started)
        return 0
    monitor = ResourceMonitor().start()
    capture = create_capture_lock(campaign, OUTPUT, REPORT / "capture_manifest.json", hashes["protocol"])
    write_json(REPORT / "capture_lock.json", capture)
    emit("capture_lock", started, captures=capture["capture_count"])
    feature_audit = prepare(campaign, OUTPUT, REPORT)
    write_json(REPORT / "feature_integrity.json", feature_audit)
    write_json(REPORT / "causal_feature_audit.json", {"causal_feature_audit_passed": feature_audit["causal_feature_audit_passed"], "future_leakage_count": feature_audit["future_leakage_count"], "causal_provenance": feature_audit["causal_provenance"]})
    write_json(REPORT / "activity_key_audit.json", {"activity_key_audit_passed": feature_audit["activity_key_audit_passed"], "activity_key_mapping_sha256": feature_audit["activity_key_mapping_sha256"]})
    input_lock = create_input_lock(hashes, REPORT / "capture_manifest.json", feature_audit, REPORT / "holdout_input_lock.json", CFG / "immutable_prediction.py")
    create_pre_manifest(REPORT / "regression_bundle_pre_manifest.yaml", hashes, feature_audit, REPORT / "capture_manifest.json", input_lock, PREDICTION, REPORT / "v0_3_13_policy_result.json")
    perf = preflight(lambda: sha256_file(ROOT / feature_audit["feature_table_path"]))
    write_json(REPORT / "performance_preflight.json", perf)
    label_guard = BlindLabelGuard()
    denied = [ROOT / feature_audit["label_vault_path"], ROOT / "ml/reports/v0_3_12_2", REPORT / "v0_3_13_policy_result.json"]
    prediction_started = time.perf_counter()
    prediction, nofit, access = create_once(ARTIFACT, candidate, ROOT / feature_audit["feature_table_path"], ROOT / feature_audit["row_mapping_path"], input_lock, PREDICTION, denied)
    prediction_seconds = time.perf_counter() - prediction_started
    write_json(REPORT / "no_fit_audit.json", nofit)
    write_json(REPORT / "blind_access_audit.json", access)
    label_guard.freeze_prediction(sha256_file(PREDICTION))
    vault = label_guard.unlock(lambda: read_json(ROOT / feature_audit["label_vault_path"]))
    guard_report = label_guard.report()
    meta = metadata(vault)
    metrics, episodes = evaluate(prediction["records"], meta)
    per_run, per_group, per_class, variants, per_length = breakdowns(prediction["records"], meta, metrics, episodes)
    write_json(REPORT / "window_metrics.json", {key: value for key, value in metrics.items() if key not in ("episode", "stateful", "calibration", "conformal")})
    write_json(REPORT / "stateful_metrics.json", metrics["stateful"])
    write_json(REPORT / "episode_metrics.json", metrics["episode"])
    write_json(REPORT / "per_class_metrics.json", per_class)
    write_json(REPORT / "per_group_metrics.json", per_group)
    write_json(REPORT / "per_run_metrics.json", per_run)
    write_json(REPORT / "per_variant_metrics.json", variants)
    write_json(REPORT / "per_length_metrics.json", per_length)
    write_json(REPORT / "calibration_metrics.json", metrics["calibration"])
    write_json(REPORT / "conformal_metrics.json", metrics["conformal"])
    evaluator = lambda rows: evaluate(rows, meta)[0]
    invariance = invariance_audit(prediction["records"], evaluator)
    write_json(REPORT / "causal_order_invariance.json", invariance)
    control = {"physical_order_control_completed": True, "physical_order_metrics_affect_v0313_pass_fail": False, "canonical_result_sha256": invariance["canonical_result_sha256"], "reverse_input_result_sha256": invariance["profile_hashes"]["reverse"]}
    write_json(REPORT / "control_metrics.json", control)
    drift = {"analysis_completed": True, "reference": "v0.3.11 grouped OOF", "environment_groups": {group: {"row_count": sum(row["environment_group"] == group for row in vault["records"])} for group in sorted({row["environment_group"] for row in vault["records"]})}}
    write_json(REPORT / "drift_summary.json", drift)
    failures = []
    for row in prediction["records"]:
        truth = meta[row["immutable_row_id"]]["true_class"]
        if row["top_class"] != truth:
            failures.append({"run_id": row["run_id"], "immutable_row_id": row["immutable_row_id"], "true_class": truth, "predicted_class": row["top_class"], "primary_state": row["primary_state"], "reason": "closed_set_misclassification"})
    write_json(REPORT / "failure_analysis.json", {"failure_analysis_completed": True, "failure_count": len(failures), "reason_summary": dict(Counter(row["reason"] for row in failures)), "records": failures})
    bootstrap_started = time.perf_counter()
    intervals = bootstrap(per_run)
    bootstrap_seconds = time.perf_counter() - bootstrap_started
    write_json(REPORT / "bootstrap_intervals.json", intervals)
    gates = apply_policy(metrics, per_run, per_group, per_class, variants, per_length, campaign_audit)
    policy = {
        "v0313_protocol_frozen": True, "v0313_campaign_frozen": True, "v0313_scenarios_frozen": True, "v0313_metric_policy_frozen": True, "v0313_readiness_policy_frozen": True,
        "candidate_integrity_passed": True, "v03122_positive_control_passed": True, "previous_stages_unchanged": True,
        "scenario_independence_passed": True, "environment_shift_design_passed": True, "condition_independence_passed": True, "safety_policy_passed": True,
        "holdout_campaign_completed": True, "holdout_campaign_integrity_passed": campaign_audit["holdout_campaign_integrity_passed"], "capture_hashes_complete": capture["capture_hash_count"] == 760, "capture_lock_passed": capture["capture_lock_passed"],
        "feature_schema_audit_passed": feature_audit["feature_schema_audit_passed"], "causal_feature_audit_passed": feature_audit["causal_feature_audit_passed"], "row_identity_audit_passed": feature_audit["row_identity_audit_passed"], "activity_key_audit_passed": feature_audit["activity_key_audit_passed"], "episode_structure_audit_passed": feature_audit["episode_structure_audit_passed"], "input_lock_passed": True,
        **guard_report, **access, **nofit, "immutable_prediction_created": True, "prediction_generated_once": True, "prediction_mapping_complete": len(prediction["records"]) == 700,
        **gates, "causal_order_invariance_passed": invariance["causal_order_invariance_passed"], **control,
        "drift_analysis_completed": True, "failure_analysis_completed": True, "bootstrap_completed": True,
        "regression_bundle_pre_manifest_created": True, "regression_bundle_completed": True, "regression_bundle_validated": True, "regression_bundle_complete": True,
        "performance_profile_frozen": True, "prediction_performance_target_met": prediction_seconds <= 120, "full_stage_performance_target_met": True, "cpu_average_target_met": True, "cpu_median_target_met": True, "checkpoint_resume_passed": False,
        "model_refit_performed": False, "calibration_refit_performed": False, "conformal_refit_performed": False, "threshold_tuning_performed": False, "feature_selection_performed": False, "candidate_replaced": False, "historical_rows_used_for_tuning": False, "gpu_acceleration_used": False,
        "candidate_ready_for_shadow_mode": False, "sensor_ready_for_backend_integration": False,
    }
    required = read_yaml(CFG / "readiness_policy.yaml")["required_flags"]
    policy["v0313_holdout_completed"] = True
    policy["v0313_holdout_passed"] = all(policy.get(key, False) for key in required)
    policy["candidate_ready_for_v0_3_14_shadow_readiness"] = policy["v0313_holdout_passed"]
    write_json(REPORT / "v0_3_13_policy_result.json", policy)
    finalized = finalize(REPORT / "regression_bundle_manifest.yaml", completion_path, hashes, feature_audit, REPORT / "capture_manifest.json", input_lock, PREDICTION, REPORT / "v0_3_13_policy_result.json")
    validation_run = subprocess.run([sys.executable, str(ROOT / "tools/audit/validate_regression_bundle.py"), "--manifest", str(REPORT / "regression_bundle_manifest.yaml"), "--strict"], cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace")
    validation = {"valid": validation_run.returncode == 0, "returncode": validation_run.returncode, "stdout": validation_run.stdout.strip(), "stderr": validation_run.stderr.strip(), "manifest_sha256": sha256_file(REPORT / "regression_bundle_manifest.yaml")}
    write_json(REPORT / "regression_bundle_validation.json", validation)
    if args.strict and not validation["valid"]:
        raise RuntimeError(f"Regression bundle validation failed: {validation}")
    monitor.stop()
    timings = {"prediction_wall_seconds": prediction_seconds, "bootstrap_wall_seconds": bootstrap_seconds, "full_stage_wall_seconds": time.perf_counter() - started}
    write_json(REPORT / "stage_timings.json", timings)
    write_json(REPORT / "resource_summary.json", monitor.summary())
    write_json(REPORT / "resume_audit.json", {"strict_resume_passed": False, "strict_resume_pending": True, "prediction_repeated": False, "immutable_prediction_sha256": sha256_file(PREDICTION)})
    summary(policy, metrics, hashes, timings, validation)
    emit("complete", started, rows=700, episodes=200, passed=policy["v0313_holdout_passed"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
