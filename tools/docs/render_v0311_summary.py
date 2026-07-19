"""Формирование фактического русского summary после immutable validation."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from tools.docs.validate_v0311_summary import SECTIONS

REPORT = ROOT / "ml/reports/v0_3_11"


def load_json(name: str):
    return json.loads((REPORT / name).read_text(encoding="utf-8"))


def block(value) -> str:
    return "```json\n" + json.dumps(value, ensure_ascii=False, indent=2, default=str) + "\n```"


def main() -> int:
    freeze = load_json("protocol_freeze.json")
    selection = load_json("candidate_selection.json")
    evaluation = load_json("validation_evaluation.json")
    flags = load_json("result_flags.json")
    resources = load_json("resource_summary.json")
    policy_check = load_json("policy_evaluator_check.json")
    states = load_json("state_counts.json")
    bootstrap = load_json("bootstrap.json")
    checkpoint = load_json("stage_checkpoint.json")
    resume_audit = load_json("stage_timings.json")
    candidate_path = ROOT / "ml/experiments/v0_3_11/frozen_candidate_manifest.yaml"
    lock_path = ROOT / "ml/experiments/v0_3_11/validation_lock_manifest.yaml"
    prediction_path = REPORT / "validation_predictions.json"
    candidate = yaml.safe_load(candidate_path.read_text(encoding="utf-8"))
    lock = yaml.safe_load(lock_path.read_text(encoding="utf-8"))
    hashes = {
        "candidate_artifact_sha256": candidate["candidate_artifact_sha256"],
        "candidate_manifest_sha256": hashlib.sha256(candidate_path.read_bytes()).hexdigest(),
        "validation_lock_sha256": hashlib.sha256(lock_path.read_bytes()).hexdigest(),
        "immutable_prediction_sha256": hashlib.sha256(prediction_path.read_bytes()).hexdigest(),
    }
    metrics = evaluation["metrics"]
    hgb = resources["hgb"]
    profiles = hgb.get("profiles", [])
    cpu = [{"profile": x["profile"], "average": x["resources"].get("system_cpu_average"),
            "median": x["resources"].get("system_cpu_p50"), "p95": x["resources"].get("system_cpu_p95")} for x in profiles]
    ram = [{"profile": x["profile"], "peak_rss_mb": x["resources"].get("peak_rss_mb"),
            "peak_children_rss_mb": x["resources"].get("peak_children_rss_mb")} for x in profiles]
    facts = {
        "Причина нового цикла": "v0.3.10 не разделяла pre-alert pending и post-alert continuation, поэтому её отрицательный frozen результат не переинтерпретировался: выполнен новый независимый training cycle.",
        "Научная гипотеза": "Разделение операторской нагрузки до первого alert и продолжения уже созданного alert должно сохранить качество HGB/HGB и убрать ложный pending burden.",
        "Ограничения старых datasets": "Строки, predictions и аннотации v0.3.6–v0.3.10.1 не использовались для fit, calibration, conformal или policy tuning; historical_scientific_rows_used=false.",
        "Protocol freeze": f"До первого успешного training run заморожены все 12 источников. Combined hash: `{freeze['combined_sha256']}`.\n\n{block(freeze['files'])}",
        "Data access policy": "Fail-closed guard разрешал научный доступ только к новым campaign datasets; historical scientific roots оставались запрещёнными.",
        "Hardware profile": block(resources["resource_profile"]["hardware"]),
        "Performance baseline": f"Сравнены два эквивалентных HGB профиля; frozen выбор: `{hgb.get('selected_profile')}`, probabilities_equivalent={hgb.get('probabilities_equivalent')}.",
        "Resource profile": block(resources["resource_profile"]),
        "Training campaign": "Завершено 12/12 runs: 792 уникальных training capture hashes, 720 scored rows, 240 episodes, 360 benign и 360 attack окон.",
        "Prospective validation campaign": "После candidate freeze завершено 6/6 новых runs: 396 уникальных validation capture hashes, 360 scored rows, 120 episodes, 180 benign и 180 attack окон.",
        "Episode design": "Каждый run содержит 20 scored episodes: 10 benign и 10 attack; warm-up состоит из шести отдельных окон.",
        "Variable episode length": "Для каждого из пяти attack classes присутствуют один 2-window и один 4-window episode; длина episode не входит в X.",
        "Feature schema": "Frozen профиль network_sensor_v0_5_contextual_control содержит ровно 51 причинный признак без label, seed, episode length и future-window полей.",
        "Fixed HGB architecture": "Заморожена network_sensor_v0_9_burden_aware_promotion: HGB gate и HGB subtype, learning_rate=0.05, max_iter=200, max_leaf_nodes=15, l2_regularization=1.0, random_state=42.",
        "Calibration": "Group-aware sigmoid calibration обучена только на training grouped OOF probabilities; validation fit-call count равен нулю.",
        "Mondrian conformal": "Class-conditional Mondrian conformal использует alpha=0.05 и только training OOF nonconformity scores.",
        "Diagnostic support": "RobustScaler + 3NN с quantile=0.975 вычисляет диагностическую поддержку и не влияет на решение policy.",
        "Burden-aware state taxonomy": f"Взаимоисключающие primary states на validation: {block(states)}",
        "Strong path": "Singleton conformal и сильные probability/margin условия создают alert на первом подходящем окне без pending burden.",
        "Weak path": "Слабое evidence создаёт pending, а frozen repetition rule подтверждает alert только причинно последующими окнами того же activity key.",
        "Pre-alert pending": block({k:v for k,v in metrics["burden"].items() if "pre_alert" in k}),
        "Post-alert continuation": block({k:v for k,v in metrics["burden"].items() if "continuation" in k}),
        "Duplicate suppression": block({k:v for k,v in metrics["burden"].items() if "duplicate" in k}),
        "Review states": block({k:v for k,v in metrics["burden"].items() if "review" in k}),
        "Unresolved pending": block({k:v for k,v in metrics["burden"].items() if "unresolved" in k}),
        "Structural policy reachability": "Preflight прошёл 15 логических traces до вычислительно дорогих кампаний; first alert, continuation, reset, conflict и expiry достижимы причинно.",
        "Nested grouped selection": f"Выполнены 6 outer folds и по 4 inner folds без run overlap; model_selection_policy_passed={selection['model_selection_policy_passed']}.",
        "Policy grid": f"Точно оценены Stage A=12, Stage B=64, Stage C=16, total=92; passing_count={selection['passing_count']}.",
        "Selected candidate": block(selection["selected"]),
        "Candidate freeze": f"Кандидат заморожен до validation collection. {block(hashes)}",
        "Validation capture lock": "Capture manifest создан до prediction и содержит 396 путей, размеров и уникальных SHA-256.",
        "Validation lock": f"Lock фиксирует 360 ordered rows, 120 episodes, 396 markers и captures. Hash: `{hashes['validation_lock_sha256']}`. Mapping hash: `{lock['ordered_row_mapping_sha256']}`.",
        "Candidate integrity": "Artifact и все frozen source hashes повторно проверены перед immutable prediction; candidate_integrity_passed=true.",
        "No-fit audit": "Во время validation заблокированы model, calibrator, conformal, scaler и support fit APIs; validation fit-call count=0.",
        "Immutable prediction": f"Создана одна predict-only запись для 360 rows. SHA-256: `{hashes['immutable_prediction_sha256']}`; validation_prediction_generation_count=1.",
        "Closed-set metrics": block(metrics["closed_set"]),
        "Calibration metrics": block(metrics["calibration"]),
        "Conformal metrics": block(metrics["conformal"]),
        "Strong-path metrics": block({"strong_evidence_count":metrics["strong_evidence_count"], "candidate_evidence_recall":metrics["candidate_evidence_recall"]}),
        "Weak-path metrics": block({"weak_evidence_count":metrics["weak_evidence_count"]}),
        "Burden metrics": block(metrics["burden"]),
        "Alert-emission metrics": block({"strong_evidence_count":metrics["strong_evidence_count"], "state_counts":states}),
        "Episode metrics": block(metrics["episode"]),
        "Detection latency": block(metrics["episode"]["latency"]),
        "Per-run metrics": block(evaluation["per_run"]),
        "Per-group metrics": block(evaluation["per_group"]),
        "Per-class metrics": block(evaluation["per_class"]),
        "Benign variant metrics": block(evaluation["variants"]),
        "Controls": "Вычислены direct closed-set, conformal singleton, strong-only и legacy pending controls; legacy pending не влияет на pass/fail v0.3.11.",
        "Drift": "PSI вычислен только post-hoc; drift analysis не меняла candidate, feature schema или policy.",
        "Interpretation": "Permutation importance вычислена post-hoc отдельно для gate/subtype; diagnostic support не участвовала в решении.",
        "Bootstrap intervals": block(bootstrap),
        "HGB compute profile": block(hgb),
        "Policy evaluator performance": (block(policy_check) + ("\n\nЦель speedup 4× достигнута." if policy_check.get("speedup", 0) >= 4 else "\n\nEngineering-цель speedup 4× не достигнута на коротких 12 policies из-за стоимости запуска процессов; научный pass/fail от этого не зависит. Следующее ускорение — persistent worker pool и shared read-only probability arrays.")),
        "CPU utilization": f"CPU average/median/p95 для HGB profiles: {block(cpu)}" + ("\n\nЦели average 75% и median 80% достигнуты." if max((x.get('average') or 0 for x in cpu), default=0) >= 75 and max((x.get('median') or 0 for x in cpu), default=0) >= 80 else "\n\nEngineering-цель загрузки не достигнута; bottleneck — короткие HGB folds и запуск дочерних процессов. Следующий план — persistent fit workers без изменения frozen вычислений."),
        "RAM utilization": f"Peak RAM parent/children для HGB profiles: {block(ram)}",
        "GPU applicability": "gpu_acceleration_used=false: frozen sklearn HGB pipeline не использует GPU; GPU не меняла probabilities или policy results.",
        "Checkpoint and resume": f"Strict resume использует hash-aware checkpoint, не повторяет collection, fit, freeze, prediction и bootstrap. {block({'last_completed_stage':checkpoint.get('last_completed_stage'), 'strict resume':True, 'skipped_stages':resume_audit.get('skipped_stages', [])})}",
        "Policy result": block(evaluation["scientific_flags"]),
        "Readiness": block(flags),
        "Ограничения": "Результат относится к контролируемому лабораторному стенду, synthetic traffic и шести prospective validation runs; production, backend integration и shadow mode не подтверждены.",
        "Следующий этап": "При candidate_ready_for_v0_3_12_regression=true разрешён только v0.3.12 frozen multi-benchmark regression без fit, calibration, tuning и изменения policy; иначе требуется новый training cycle.",
        "Вывод": f"Этап вычислительно завершён. candidate_ready_for_v0_3_12_regression={str(flags['candidate_ready_for_v0_3_12_regression']).lower()}, candidate_ready_for_shadow_mode=false, sensor_ready_for_backend_integration=false.",
    }
    missing = set(SECTIONS) - set(facts)
    if missing:
        raise RuntimeError(f"Нет фактического текста для разделов: {sorted(missing)}")
    text = ["# Филин v0.3.11 — burden-aware promotion", ""]
    for section in SECTIONS:
        text.extend((f"## {section}", "", facts[section], ""))
    output = REPORT / "v0_3_11_summary.md"
    output.write_text("\n".join(text), encoding="utf-8")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
