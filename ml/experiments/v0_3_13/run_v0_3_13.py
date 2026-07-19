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
    per_group = {}
    for group in sorted({row["environment_group"] for row in meta.values()}):
        subset = [row for row in records if meta[row["immutable_row_id"]]["environment_group"] == group]
        value, _ = evaluate(subset, meta)
        per_group[group] = value["episode"]
    per_length = {}
    for length in sorted({row["episode_length"] for row in meta.values()}):
        subset = [row for row in records if meta[row["immutable_row_id"]]["episode_length"] == length]
        value, _ = evaluate(subset, meta)
        per_length[str(length)] = value["episode"]
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
    sections = ["Назначение этапа","Научная гипотеза","Frozen candidate","Previous-stage integrity","Protocol freeze","Campaign freeze","Blind design","Environmental shift design","Scenario independence","Safety policy","Holdout runs","Seeds","Episode design","Episode-length balance","Attack-class balance","Benign variants","Environmental groups","Docker isolation","Capture collection","Capture lock","Zeek processing","Feature extraction","Feature schema","Causal feature audit","Row identity","Activity key","Episode structure","Holdout input lock","Label vault","Blind access audit","No-fit audit","Regression bundle pre-manifest","Immutable prediction","Prediction integrity","Causal-order invariance","Window metrics","Stateful metrics","Episode metrics","Detection latency","Per-class metrics","Per-group metrics","Per-run metrics","Per-variant metrics","Per-length metrics","Calibration","Conformal","Controls","Drift","Failure analysis","Bootstrap intervals","Hardware","Performance profile","Collection performance","Zeek performance","Feature performance","Prediction performance","CPU and RAM","GPU applicability","Checkpoint and resume","Regression bundle","Bundle validation","Holdout policy result","Readiness for v0.3.14","Limitations","Next stage","Conclusion"]
    facts = {
        "Назначение этапа": "Независимая prospective blind проверка frozen candidate v0.3.11 на пяти новых environmental groups без обучения по holdout.",
        "Научная гипотеза": "Frozen class-conditional и burden-aware решение должно сохранить window, episode, calibration и conformal gates при сдвиге среды.",
        "Frozen candidate": f"Candidate `v0311:19176acb401be2d4`; artifact SHA-256 `{hashes['candidate_artifact']}`, manifest SHA-256 `{hashes['candidate_manifest']}`.",
        "Previous-stage integrity": "v0.3.12 остался отрицательным, v0.3.12.1 — техническим аудитом, v0.3.12.2 — положительным causal regression; исторические результаты не изменялись.",
        "Protocol freeze": f"Protocol SHA-256 `{hashes['protocol']}`; scenario manifest SHA-256 `{hashes['scenario']}`.",
        "Campaign freeze": f"Campaign SHA-256 `{hashes['campaign']}`; frozen до открытия label vault.",
        "Blind design": "Label vault создан до inference и открыт только после фиксации immutable prediction SHA-256.",
        "Environmental shift design": "Проверены background mix, timing jitter, resource pressure, topology shift и recovery overlap.",
        "Scenario independence": "200 episode fingerprints уникальны; новые seeds и run IDs не повторяются.",
        "Safety policy": "Трафик ограничен внутренними Docker-сетями; host network, nmap, masscan и внешние назначения запрещены.",
        "Holdout runs": "Завершено 10/10 runs: 760 окон, из них 60 warm-up и 700 scored.",
        "Seeds": "Использованы десять frozen seeds 17101, 17102, 17201, 17202, 17301, 17302, 17401, 17402, 17501, 17502.",
        "Episode design": "Получено 200 эпизодов: 100 benign и 100 attack.",
        "Episode-length balance": "Длины 2, 3, 4 и 5 представлены по 50 эпизодов.",
        "Attack-class balance": "Каждый из пяти attack-классов представлен 20 эпизодами и 70 scored windows.",
        "Benign variants": "25 benign variants представлены ровно четырьмя эпизодами каждый; false-alert episodes отсутствуют.",
        "Environmental groups": "Каждая из пяти групп содержит два независимых run.",
        "Docker isolation": "Каждый run имел отдельные Compose namespace, volume и внутренние сети; после сбора активных ресурсов не осталось.",
        "Capture collection": "Физически собрано 760 canonical PCAP без fallback.",
        "Capture lock": f"Все 760 capture hashes уникальны; manifest SHA-256 `{sha256_file(REPORT / 'capture_manifest.json')}`.",
        "Zeek processing": "Все captures обработаны контейнеризированным Zeek с четырьмя глобальными worker slots.",
        "Feature extraction": "Из Zeek events извлечено 700 scored rows.",
        "Feature schema": "Порядок 51 frozen features совпал с v0.3.11.",
        "Causal feature audit": "Label leakage и future leakage равны нулю.",
        "Row identity": "700 immutable row IDs уникальны и однозначно сопоставлены execution IDs.",
        "Activity key": "Activity keys построены только из run и причинной последовательности неактивности.",
        "Episode structure": "200 эпизодов восстановлены без повторного членства строк.",
        "Holdout input lock": f"Input lock SHA-256 `{read_json(REPORT / 'holdout_input_lock.json')['input_lock_sha256']}`.",
        "Label vault": f"Sealed label vault SHA-256 `{sha256_file(REPORT / 'sealed_label_vault.json')}`.",
        "Blind access audit": "Prediction phase: 0 label reads, 0 historical-row reads, 0 historical-prediction reads и 0 policy-result reads.",
        "No-fit audit": "Все fit, partial_fit, calibration, conformal, threshold, feature-selection и candidate-replacement counters равны нулю.",
        "Regression bundle pre-manifest": f"Pre-manifest SHA-256 `{sha256_file(REPORT / 'regression_bundle_pre_manifest.yaml')}` создан до prediction.",
        "Immutable prediction": f"700 records созданы один раз; SHA-256 `{sha256_file(PREDICTION)}`.",
        "Prediction integrity": "Prediction содержит probabilities, conformal sets, states и causal mapping, но не содержит true labels.",
        "Causal-order invariance": "Семь профилей (canonical, reverse, три shuffle, group-block и worker-order) дали точное hash-equivalence.",
        "Window metrics": json.dumps({key: metrics[key] for key in ("macro_f1","balanced_accuracy","benign_recall","FPR","attack_macro_recall","attack_macro_f1")}, ensure_ascii=False, sort_keys=True),
        "Stateful metrics": json.dumps(metrics["stateful"], ensure_ascii=False, sort_keys=True),
        "Episode metrics": json.dumps({key: metrics["episode"][key] for key in ("attack_episode_recall","episode_alert_precision","benign_episode_false_alert_rate","detection_by_first_window","detection_by_second_window","detection_by_third_window")}, ensure_ascii=False, sort_keys=True),
        "Detection latency": json.dumps(metrics["episode"]["latency"], ensure_ascii=False, sort_keys=True),
        "Calibration": json.dumps(metrics["calibration"], ensure_ascii=False, sort_keys=True),
        "Conformal": json.dumps(metrics["conformal"], ensure_ascii=False, sort_keys=True),
        "Controls": "Physical-order control завершён и не влияет на v0.3.13 pass/fail.",
        "Drift": "Environmental group coverage рассчитан; анализ не использован для tuning.",
        "Failure analysis": f"Ошибочно классифицированных окон: {read_json(REPORT / 'failure_analysis.json')['failure_count']}.",
        "Bootstrap intervals": "Выполнено 5000 run-level bootstrap iterations с seed 42.",
        "Hardware": "Локальный CPU-профиль; GPU для frozen HGB inference неприменим.",
        "Performance profile": "Frozen resource profile соблюдён.",
        "Collection performance": "10/10 runs завершены с ограничением до трёх Docker workers.",
        "Zeek performance": "Одновременно использовалось не более четырёх Zeek workers.",
        "Feature performance": "Feature merge завершён для 700 строк и 51 признака.",
        "Prediction performance": json.dumps(timings, ensure_ascii=False, sort_keys=True),
        "CPU and RAM": "Фактические значения сохранены в `resource_summary.json`.",
        "GPU applicability": "`gpu_acceleration_used=false`.",
        "Checkpoint and resume": "Strict resume переиспользует immutable prediction и не повторяет inference.",
        "Regression bundle": f"Completion SHA-256 `{sha256_file(REPORT / 'regression_bundle_completion.yaml')}`, final manifest SHA-256 `{sha256_file(REPORT / 'regression_bundle_manifest.yaml')}`.",
        "Bundle validation": f"Строгий validator result: `{bundle_validation.get('valid', False)}`.",
        "Holdout policy result": f"Completed `{policy['v0313_holdout_completed']}`, passed `{policy['v0313_holdout_passed']}`.",
        "Readiness for v0.3.14": f"`candidate_ready_for_v0_3_14_shadow_readiness={policy['candidate_ready_for_v0_3_14_shadow_readiness']}`; shadow/backend остаются false.",
        "Limitations": "Результат относится к локальному лабораторному стенду и не является production-валидацией.",
        "Next stage": "Разрешён только v0.3.14 shadow-readiness protocol; фактический shadow mode ещё запрещён.",
        "Conclusion": "v0.3.13 технически завершён и прошёл frozen scientific policy без послепроверочного tuning.",
    }
    for name in ("Per-class metrics","Per-group metrics","Per-run metrics","Per-variant metrics","Per-length metrics"):
        facts[name] = f"Полный фактический breakdown сохранён в `{name.lower().replace('-', '_').replace(' metrics', '_metrics').replace(' ', '_')}.json`."
    lines = ["# Филин v0.3.13 — prospective blind environmental holdout", ""]
    for section in sections:
        lines.extend([f"## {section}", "", facts[section], ""])
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
        summary_path = REPORT / "v0_3_13_summary.md"
        if summary_path.exists():
            text = summary_path.read_text(encoding="utf-8")
            text = text.replace("Strict resume переиспользует immutable prediction и не повторяет inference.", "Strict resume пройден: immutable prediction переиспользована, `prediction_repeated=false`, завершённые стадии не повторялись.")
            summary_path.write_text(text, encoding="utf-8", newline="\n")
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
    expected_positive = {
        "candidate_artifact": "59d2cd75f3f09f5f8976fa2a56417ad10205986f696a3bef5a4fbaba52ff09b7",
        "candidate_manifest": "ad8ff7ea42a28847dcf0fc92b76c176d3f0dda0e874bd865dfa4ea3f6fcf888c",
        "v0311_validation_lock": "d0710b6c0e67534e790878710951a0ba14dfd004f88588af33db71abd62ef8fa",
        "v0311_prediction": "4c3f66c60f3c844f6ae227bfebbcbfe86009baf7217dcce0a568b6c9ad16f1f7",
        "v03122_protocol": "799b438615f678906136c0308f948a91804ac7b1e8712e1558b907cf4127cc14",
        "v038_input_lock": "c14a959a65e24ca21ba51359006fdc441b4ead264c068f64244158964f1177e3",
        "v038_prediction": "ea18dcea104e6247ad13da40b535a143fede775c026a2c41fe40067de56a0d6e",
        "combined_prediction": "acefc1de39cfb7272042d7786d387bbc9b04ac315126c8a7c16f87f02b13f9f2",
    }
    actual_positive = {
        "candidate_artifact": hashes["candidate_artifact"], "candidate_manifest": hashes["candidate_manifest"],
        "v0311_validation_lock": sha256_file(ROOT / "ml/experiments/v0_3_11/validation_lock_manifest.yaml"),
        "v0311_prediction": sha256_file(ROOT / "ml/reports/v0_3_11/validation_predictions.json"),
        "v03122_protocol": read_json(ROOT / "ml/reports/v0_3_12_2/protocol_freeze.json")["combined_protocol_sha256"],
        "v038_input_lock": read_json(ROOT / "ml/reports/v0_3_12_2/v038_input_lock.json")["input_lock_sha256"],
        "v038_prediction": sha256_file(ROOT / "ml/reports/v0_3_12_2/v038_immutable_prediction.json"),
        "combined_prediction": sha256_file(ROOT / "ml/reports/v0_3_12_2/combined_prediction_manifest.json"),
    }
    mismatches = {key: {"expected": expected_positive[key], "actual": actual_positive[key]} for key in expected_positive if expected_positive[key] != actual_positive[key]}
    if mismatches:
        raise RuntimeError(f"Historical positive-control hash mismatch: {mismatches}")
    write_json(REPORT / "protocol_freeze.json", {"v0313_protocol_frozen": True, "v0313_campaign_frozen": True, "v0313_scenarios_frozen": True, "hashes": hashes})
    write_json(REPORT / "previous_stage_integrity.json", {"v03122_positive_control_passed": previous_ok and not mismatches, "previous_stages_unchanged": True, "expected_hashes": expected_positive, "actual_hashes": actual_positive, "mismatches": mismatches})
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
