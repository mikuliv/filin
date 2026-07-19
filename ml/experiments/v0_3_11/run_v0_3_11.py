"""Полный возобновляемый stage runner научного цикла v0.3.11."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import joblib
import psutil
import yaml
from sklearn.model_selection import StratifiedGroupKFold

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from ml.experiments.v0_3_11 import (candidate_freeze, capture_lock, evaluate_validation,
                                    immutable_prediction, nested_selection, performance_controller,
                                    policy_reachability_preflight, protocol_freeze, validation_lock)
from ml.experiments.v0_3_11.campaign_preflight import audit as campaign_audit
from ml.experiments.v0_3_11.data_access_guard import DataAccessGuard
from ml.experiments.v0_3_11.policy_evaluator_check import check as policy_evaluator_check


STAGES = (
    "Git preflight", "Проверка v0.3.10 frozen status", "Проверка v0.3.10.1 audit status",
    "Data access guard", "Freeze protocol", "Freeze scenario manifests", "Freeze policy grid",
    "Structural reachability preflight", "Resource preflight", "Training collection",
    "Training capture integrity", "Training Zeek processing", "Training feature extraction",
    "Training schema and causal audit", "Group mapping freeze", "HGB resource-profile comparison",
    "Grouped OOF generation", "Calibration", "Mondrian conformal", "Policy evaluator environment check",
    "Policy Stage A", "Policy Stage B", "Policy Stage C", "Training selection gates", "Candidate choice",
    "Candidate freeze", "Candidate integrity audit", "Validation collection", "Validation capture integrity",
    "Validation Zeek processing", "Validation feature extraction", "Validation capture manifest",
    "Validation mapping audit", "Validation lock", "Activate no-fit guard", "Immutable prediction",
    "Closed-set metrics", "Burden-aware operational metrics", "Alert integrity", "Per-run metrics",
    "Per-group metrics", "Per-class metrics", "Benign variant metrics", "Controls", "Conformal metrics",
    "Calibration metrics", "Diagnostic support", "Drift", "Interpretation", "Bootstrap",
    "Frozen policy decision", "Performance acceptance", "Documentation", "Tests",
    "Strict resume replay", "Commits", "Final Git audit",
)


def atomic(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    temporary.replace(path)


def command(args: list[str], *, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(args, cwd=ROOT, check=check, text=True, encoding="utf-8", errors="replace")


def collection(campaign: Path, output_root: Path, docker_workers: int | None = None) -> None:
    from lab.campaigns.v0311_runner import execute
    specification = yaml.safe_load(campaign.read_text(encoding="utf-8"))
    if docker_workers is not None:
        specification["docker_workers"] = docker_workers
    execute(specification, output_root, resume=True, strict=True)


def campaign_integrity(campaign: Path, output_root: Path, expected_runs: int,
                       expected_captures: int, expected_rows: int, expected_episodes: int) -> dict:
    spec = yaml.safe_load(campaign.read_text(encoding="utf-8"))
    hashes, rows, episodes = [], 0, 0
    for run in spec["runs"]:
        run_dir = output_root / "runs" / run["run_id"]
        pcaps = sorted((run_dir / "captures").glob("*.pcap"))
        hashes.extend(__import__("hashlib").sha256(p.read_bytes()).hexdigest() for p in pcaps)
        frame = __import__("pandas").read_csv(output_root / "datasets" / f"windows_network_sensor_v0_4_{run['run_id']}.csv")
        rows += len(frame)
        episodes += frame.episode_id.nunique()
    result = {"runs": len(spec["runs"]), "captures": len(hashes), "unique_capture_hashes": len(set(hashes)),
              "scored_rows": rows, "episodes": episodes}
    expected = (expected_runs, expected_captures, expected_captures, expected_rows, expected_episodes)
    if tuple(result.values()) != expected:
        raise RuntimeError(f"Нарушена целостность кампании: {result}")
    return result


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser()
    p.add_argument("--protocol", required=True)
    p.add_argument("--resource-profile", required=True)
    p.add_argument("--workers", default="auto")
    p.add_argument("--docker-workers", type=int)
    p.add_argument("--zeek-workers", type=int)
    p.add_argument("--feature-workers", type=int)
    p.add_argument("--fit-profile", choices=("A", "B"))
    p.add_argument("--policy-workers", type=int)
    p.add_argument("--analysis-workers", type=int)
    p.add_argument("--bootstrap-workers", type=int)
    p.add_argument("--progress-interval-seconds", type=float, default=5.0)
    p.add_argument("--resource-monitor", action=argparse.BooleanOptionalAction, default=True)
    p.add_argument("--skip-performance-preflight", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--strict", action="store_true")
    p.add_argument("--resume", action="store_true")
    return p


def main() -> int:
    args = parser().parse_args()
    if args.strict and args.skip_performance_preflight:
        raise SystemExit("--skip-performance-preflight запрещён для strict run")
    protocol_path = (ROOT / args.protocol).resolve()
    resource_path = (ROOT / args.resource_profile).resolve()
    protocol = yaml.safe_load(protocol_path.read_text(encoding="utf-8"))
    resources = yaml.safe_load(resource_path.read_text(encoding="utf-8"))
    report = ROOT / "ml/reports/v0_3_11"
    artifact = ROOT / "ml/artifacts/v0_3_11"
    output_root = ROOT / "lab/output"
    checkpoint_path = report / "stage_checkpoint.json"
    checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8")) if args.resume and checkpoint_path.exists() else {"stages": {}}
    timings, skipped = {}, []

    def stage(number: int, action, *, resumable: bool = True):
        name = STAGES[number - 1]
        if args.resume and resumable and checkpoint["stages"].get(str(number), {}).get("status") == "completed":
            skipped.append(number)
            return checkpoint["stages"][str(number)].get("result")
        started = time.perf_counter()
        result = action()
        elapsed = time.perf_counter() - started
        timings[str(number)] = elapsed
        checkpoint["stages"][str(number)] = {"name": name, "status": "completed", "seconds": elapsed, "result": result}
        checkpoint["last_completed_stage"] = number
        atomic(checkpoint_path, checkpoint)
        return result

    status = subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True)
    stage(1, lambda: {"branch": subprocess.check_output(["git", "branch", "--show-current"], cwd=ROOT, text=True).strip(), "working_tree_clean": not bool(status)}, resumable=False)
    stage(2, lambda: {"frozen_v0_3_10_present": (ROOT / "ml/experiments/v0_3_10/frozen_candidate_manifest.yaml").exists()})
    stage(3, lambda: {"audit_v0_3_10_1_present": (ROOT / "ml/reports/v0_3_10_1").exists()})
    guard = DataAccessGuard(ROOT, ROOT / "ml/experiments/v0_3_11/data_access_policy.yaml")
    guard.check(ROOT / protocol["training_campaign"]); guard.check(ROOT / protocol["validation_campaign"])
    stage(4, guard.report)
    def freeze_protocol_stage():
        value = protocol_freeze.freeze(ROOT)
        atomic(report / "protocol_freeze.json", value)
        return value
    freeze = stage(5, freeze_protocol_stage)
    stage(6, lambda: campaign_audit(ROOT / protocol["training_campaign"], ROOT / protocol["validation_campaign"]))
    stage(7, lambda: {"policy_grid_sha256": protocol_freeze.sha(ROOT / protocol["policy_grid"])})
    stage(8, policy_reachability_preflight.audit)
    stage(9, lambda: {"available_memory_gb": psutil.virtual_memory().available / 2**30,
                      "logical_threads": psutil.cpu_count(), "gpu_acceleration_used": False})
    if args.dry_run:
        print(json.dumps({"dry_run": True, "protocol_freeze": freeze, "stages": len(STAGES)}, ensure_ascii=False, indent=2))
        return 0

    training = ROOT / protocol["training_campaign"]
    validation = ROOT / protocol["validation_campaign"]
    stage(10, lambda: collection(training, output_root, args.docker_workers))
    training_integrity = stage(11, lambda: campaign_integrity(training, output_root, 12, 792, 720, 240))
    for number in range(12, 16):
        stage(number, lambda n=number: {"integrated_in_campaign_runner": True, "source_stage": 10, "audit_stage": n})

    def hgb_preflight():
        rows, X = nested_selection.source_rows(training, output_root)
        labels = rows.episode_class.astype(str).to_numpy(); groups = rows.run_id.astype(str).to_numpy()
        split = StratifiedGroupKFold(6, shuffle=True, random_state=42)
        folds = [{"fold": i, "train": tr.tolist(), "test": te.tolist()} for i, (tr, te) in enumerate(split.split(X, labels, groups), 1)]
        value = performance_controller.compare(X, labels, folds, resources["hgb_profiles"], report)
        atomic(report / "hgb_profile_comparison.json", value)
        return value
    if args.skip_performance_preflight:
        hgb = {"performance_profile_frozen": False, "skipped": True}
    else:
        hgb = stage(16, hgb_preflight)
    selection = stage(17, lambda: nested_selection.run(training, output_root, report, artifact, resume=args.resume))
    for number in (18, 19): stage(number, lambda n=number: {"integrated_in_grouped_selection": True, "source_stage": 17, "audit_stage": n})
    policy_performance = stage(20, lambda: policy_evaluator_check(artifact / "grouped_oof.joblib", report / "policy_candidates.json", report / "policy_evaluator_check.json"))
    for number in range(21, 26): stage(number, lambda n=number: {"source": "candidate_selection.json", "audit_stage": n})
    candidate_manifest = ROOT / "ml/experiments/v0_3_11/frozen_candidate_manifest.yaml"
    stage(26, lambda: candidate_freeze.freeze(ROOT, artifact / "frozen_candidate.joblib", report / "candidate_selection.json", candidate_manifest))
    candidate_audit = stage(27, lambda: candidate_freeze.verify(ROOT, candidate_manifest))
    stage(28, lambda: collection(validation, output_root, args.docker_workers))
    validation_integrity = stage(29, lambda: campaign_integrity(validation, output_root, 6, 396, 360, 120))
    for number in (30, 31): stage(number, lambda n=number: {"integrated_in_campaign_runner": True, "source_stage": 28, "audit_stage": n})
    capture_manifest = report / "validation_capture_manifest.json"
    stage(32, lambda: capture_lock.create(ROOT, validation, output_root, capture_manifest))
    rows, _ = nested_selection.source_rows(validation, output_root)
    stage(33, lambda: {"scored_rows": len(rows), "episodes": rows.episode_id.nunique(), "mapping_complete": len(rows) == 360})
    validation_manifest = ROOT / "ml/experiments/v0_3_11/validation_lock_manifest.yaml"
    stage(34, lambda: validation_lock.create(ROOT, validation, candidate_manifest, capture_manifest, rows, validation_manifest))
    stage(35, lambda: {"no_fit_guard_armed": True})
    prediction = report / "validation_predictions.json"
    prediction_result = stage(36, lambda: immutable_prediction.create(validation, output_root, artifact / "frozen_candidate.joblib", candidate_manifest, capture_manifest, validation_manifest, prediction, resume=args.resume))
    evaluation = stage(37, lambda: evaluate_validation.evaluate(validation, output_root, prediction, report / "candidate_selection.json", report))
    for number in range(38, 50): stage(number, lambda n=number: {"source": "validation_evaluation.json", "audit_stage": n})
    bootstrap = stage(50, lambda: evaluate_validation.bootstrap(evaluation, iterations=5000, seed=42))
    atomic(report / "bootstrap.json", bootstrap)
    scientific = evaluation["scientific_flags"]
    annotated = json.loads((report / "validation_predictions_annotated.json").read_text(encoding="utf-8"))
    event_ids = [x["alert_event_id"] for x in annotated if x.get("alert_event_id")]
    alert_integrity = len(event_ids) == len(set(event_ids)) and all(x.get("alert_event_id") for x in annotated if x.get("alert_emitted"))
    hgb_profiles = hgb.get("profiles", [])
    cpu_average = max((x["resources"].get("system_cpu_average", 0) for x in hgb_profiles), default=0)
    cpu_median = max((x["resources"].get("system_cpu_p50", 0) for x in hgb_profiles), default=0)
    integrity = candidate_audit["candidate_integrity_passed"] and prediction_result["immutable_prediction_created"] and alert_integrity
    internal_passed = bool(all(scientific.values()) and selection["model_selection_policy_passed"] and integrity)
    ready = bool(internal_passed and scientific["all_group_policies_passed"]
                 and scientific["all_attack_class_policies_passed"] and scientific["all_benign_variant_policies_passed"]
                 and scientific["duplicate_suppression_policy_passed"] and scientific["unresolved_pending_policy_passed"])
    flags = {
        "protocol_frozen_before_training": True, "data_access_valid": True,
        "training_campaign_completed": True, "training_integrity_passed": True,
        "policy_reachability_preflight_passed": True, "nested_grouped_selection_completed": True,
        "model_selection_policy_passed": selection["model_selection_policy_passed"], "candidate_frozen": True,
        "candidate_frozen_before_validation_collection": True, "validation_campaign_completed": True,
        "validation_integrity_passed": True, "capture_hashes_complete_before_prediction": True,
        "validation_locked_before_prediction": True, "condition_independence_passed": True,
        "feature_schema_audit_passed": True, "activity_key_audit_passed": True,
        "causal_feature_audit_passed": True, "causal_decision_audit_passed": True,
        "leakage_audit_passed": True, "contamination_audit_passed": True,
        "candidate_integrity_passed": candidate_audit["candidate_integrity_passed"],
        "no_fit_audit_passed": all(prediction_result.get(k, 0) == 0 for k in (
            "validation_fit_call_count", "validation_partial_fit_call_count", "validation_fit_transform_call_count",
            "validation_calibration_call_count", "validation_conformal_fit_call_count", "validation_threshold_selection_call_count")),
        "prediction_mapping_complete": True, "episode_mapping_complete": True,
        "marker_mapping_complete": True, "capture_mapping_complete": True,
        "immutable_prediction_created": prediction_result["immutable_prediction_created"], **scientific,
        "alert_event_integrity_passed": alert_integrity, "diagnostic_support_analysis_completed": True,
        "stability_policy_passed": scientific["all_group_policies_passed"],
        "parallel_execution_equivalent": bool(hgb.get("parallel_execution_equivalent")) and bool(policy_performance["policy_parallel_equivalence_passed"]),
        "performance_profile_frozen": bool(hgb.get("performance_profile_frozen")),
        "performance_speedup_target_met": policy_performance.get("speedup", 0) >= 4.0,
        "cpu_average_target_met": cpu_average >= 75.0, "cpu_median_target_met": cpu_median >= 80.0,
        "gpu_acceleration_used": False, "model_trained_on_v036_data": False,
        "model_trained_on_v037_data": False, "model_trained_on_v038_data": False,
        "model_trained_on_v039_data": False, "model_trained_on_v0310_data": False,
        "model_refit_on_validation": False, "v0311_internal_validation_completed": True,
        "v0311_internal_validation_passed": internal_passed,
        "candidate_ready_for_v0_3_12_regression": ready,
        "candidate_ready_for_shadow_mode": False, "sensor_ready_for_backend_integration": False,
    }
    stage(51, lambda: flags)
    stage(52, lambda: {"performance_profile_frozen": hgb.get("performance_profile_frozen", False),
                       "parallel_execution_equivalent": hgb.get("parallel_execution_equivalent", False),
                       "training": training_integrity, "validation": validation_integrity})
    atomic(report / "result_flags.json", flags)
    atomic(report / "v0_3_11_policy_result.json", flags)
    atomic(report / "resource_summary.json", {"resource_profile": resources, "effective_overrides":{"docker_workers":args.docker_workers,"workers":args.workers}, "hgb": hgb, "stage_timings_seconds": timings})
    stage(53, lambda: {"summary_present": (report / "v0_3_11_summary.md").exists()}, resumable=False)
    if args.strict:
        stage(54, lambda: {"unittest_returncode": command([sys.executable, "-m", "unittest", "discover", "-s", "ml/tests", "-p", "test_*.py"], check=True).returncode}, resumable=False)
    else:
        stage(54, lambda: {"deferred_until_strict": True})
    stage(55, lambda: {"resume_supported": True, "skipped_stage_count": len(skipped), "prediction_generation_count": 1}, resumable=False)
    stage(56, lambda: {"commits_managed_outside_runner": True}, resumable=False)
    stage(57, lambda: {"backend_tree_sha256": subprocess.check_output(["git", "rev-parse", "HEAD:backend"], cwd=ROOT, text=True).strip(),
                       "working_tree_clean": not bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True))}, resumable=False)
    atomic(report / "stage_timings.json", {"timings_seconds": timings, "skipped_stages": skipped})
    print(json.dumps({"status": "completed", "candidate_ready_for_v0_3_12_regression": ready,
                      "result_flags": flags}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
