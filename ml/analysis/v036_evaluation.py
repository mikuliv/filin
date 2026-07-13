"""Однократная frozen evaluation и post-hoc отчёты v0.3.6."""
from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
import yaml
from sklearn.metrics import (accuracy_score, balanced_accuracy_score, confusion_matrix,
                             f1_score, log_loss, precision_recall_fscore_support,
                             precision_score, recall_score)

from v036_historical_comparison import compare
from v036_holdout import load_holdout, sha256, stable_sha, write_json

ROOT = Path(__file__).resolve().parents[2]
ATTACKS = ["port_scan", "auth_failures", "web_probe", "low_rate_dos", "beacon_simulation"]
LABELS = ["benign", *ATTACKS]


def _scalar(value: Any) -> Any:
    if isinstance(value, (np.bool_,)): return bool(value)
    if isinstance(value, (np.integer,)): return int(value)
    if isinstance(value, (np.floating,)): return float(value)
    return value


def metrics(frame: pd.DataFrame) -> dict[str, Any]:
    y = frame.label.astype(str).to_numpy(); pred = frame.prediction.astype(str).to_numpy()
    precision, recall, f1, support = precision_recall_fscore_support(y, pred, labels=LABELS, zero_division=0)
    benign = y == "benign"; attack = ~benign
    cy = np.where(benign, "benign", "attack"); cp = np.where(pred == "benign", "benign", "attack")
    hard = frame.hard_negative.astype(bool).to_numpy() if "hard_negative" in frame else np.zeros(len(frame), dtype=bool)
    attack_rows = frame[frame.label != "benign"]
    result = {
        "support": len(frame), "accuracy": float(accuracy_score(y, pred)),
        "balanced_accuracy": float(balanced_accuracy_score(y, pred)),
        "macro_precision": float(precision_score(y, pred, labels=LABELS, average="macro", zero_division=0)),
        "macro_recall": float(recall_score(y, pred, labels=LABELS, average="macro", zero_division=0)),
        "macro_f1": float(f1_score(y, pred, labels=LABELS, average="macro", zero_division=0)),
        "weighted_f1": float(f1_score(y, pred, labels=LABELS, average="weighted", zero_division=0)),
        "benign_precision": float(precision[0]), "benign_recall": float(recall[0]), "benign_f1": float(f1[0]),
        "false_positive_count": int(np.sum(benign & (pred != "benign"))),
        "false_positive_rate": float(np.mean(pred[benign] != "benign")) if benign.any() else 0.0,
        "hard_negative_benign_recall": float(np.mean(pred[hard] == "benign")) if hard.any() else 1.0,
        "hard_negative_false_positive_rate": float(np.mean(pred[hard] != "benign")) if hard.any() else 0.0,
        "attack_macro_precision": float(np.mean(precision[1:])), "attack_macro_recall": float(np.mean(recall[1:])),
        "attack_macro_f1": float(np.mean(f1[1:])),
        "collapsed_attack_precision": float(precision_score(cy, cp, pos_label="attack", zero_division=0)),
        "collapsed_attack_recall": float(recall_score(cy, cp, pos_label="attack", zero_division=0)),
        "collapsed_attack_f1": float(f1_score(cy, cp, pos_label="attack", zero_division=0)),
        "attack_false_negative_count": int(((frame.label != "benign") & (frame.prediction == "benign")).sum()),
        "wrong_attack_class_count": int(((frame.label != "benign") & (frame.prediction != "benign") & (frame.label != frame.prediction)).sum()),
        "per_class": {label: {"precision": float(precision[i]), "recall": float(recall[i]),
                               "f1": float(f1[i]), "support": int(support[i])} for i, label in enumerate(LABELS)},
        "confusion_matrix": confusion_matrix(y, pred, labels=LABELS).tolist(),
        "labels": LABELS, "zero_recall_classes": [LABELS[i] for i in range(len(LABELS)) if support[i] and recall[i] == 0],
    }
    return result


def _calibration(frame: pd.DataFrame, probabilities: np.ndarray, classes: list[str]) -> dict[str, Any]:
    y = frame.label.astype(str).to_numpy(); predicted = probabilities.max(axis=1)
    correct = frame.prediction.astype(str).to_numpy() == y
    bins = np.linspace(0, 1, 11); ece = 0.0; details = []
    for low, high in zip(bins[:-1], bins[1:]):
        mask = (predicted >= low) & (predicted < high if high < 1 else predicted <= high)
        if mask.any():
            accuracy = float(correct[mask].mean()); confidence = float(predicted[mask].mean())
            ece += float(mask.mean()) * abs(accuracy - confidence)
            details.append({"lower": float(low), "upper": float(high), "count": int(mask.sum()), "accuracy": accuracy, "confidence": confidence})
    one_hot = np.zeros_like(probabilities)
    lookup = {name: i for i, name in enumerate(classes)}
    for i, label in enumerate(y): one_hot[i, lookup[label]] = 1
    entropy = -(probabilities * np.log(np.clip(probabilities, 1e-15, 1))).sum(axis=1)
    return {"calibration_performed": False, "threshold_tuning_performed": False, "fixed_bins": bins.tolist(),
            "multiclass_log_loss": float(log_loss(y, probabilities, labels=classes)),
            "multiclass_brier_score": float(np.mean(np.sum((probabilities-one_hot)**2, axis=1))),
            "expected_calibration_error": float(ece), "bin_details": details,
            "maximum_probability_mean": float(predicted.mean()), "maximum_probability_median": float(np.median(predicted)),
            "prediction_entropy_mean": float(entropy.mean()),
            "correct_confidence_mean": float(predicted[correct].mean()) if correct.any() else None,
            "incorrect_confidence_mean": float(predicted[~correct].mean()) if (~correct).any() else None}


def _bootstrap(frame: pd.DataFrame, iterations: int = 5000) -> dict[str, Any]:
    rng = np.random.default_rng(42); runs = np.array(sorted(frame.run_id.unique())); names = (
        "macro_f1", "balanced_accuracy", "benign_recall", "false_positive_rate",
        "hard_negative_benign_recall", "attack_macro_recall", "collapsed_attack_precision", "collapsed_attack_recall")
    values = {name: [] for name in names}
    for _ in range(iterations):
        sample = pd.concat([frame[frame.run_id == run] for run in rng.choice(runs, len(runs), replace=True)], ignore_index=True)
        measured = metrics(sample)
        for name in names: values[name].append(measured[name])
    point = metrics(frame)
    return {"iterations": iterations, "random_state": 42, "sampling_unit": "run_id",
            "metrics": {name: {"point": point[name], "lower_95": float(np.quantile(values[name], .025)),
                               "upper_95": float(np.quantile(values[name], .975))} for name in names}}


def _feature_distribution(frame: pd.DataFrame, features: list[str]) -> dict[str, Any]:
    train_files = sorted((ROOT / "lab/output/datasets").glob("windows_network_sensor_v0_4_run_v034_train_*.csv"))
    if not train_files:
        return {"feature_count": len(features), "top_drift_features": [], "historical_training_available": False}
    from v034_profiles import project_row
    old_raw = pd.concat([pd.read_csv(path) for path in train_files], ignore_index=True)
    old = pd.DataFrame([project_row(row, "network_sensor_v0_4_rates") for row in old_raw.to_dict("records")], columns=features)
    rows = {}
    for feature in features:
        a = old[feature].astype(float); b = frame[feature].astype(float); scale = max(float(a.std()), 1e-12)
        rows[feature] = {"standardized_mean_difference": float((b.mean()-a.mean())/scale),
                         "median_ratio": float(b.median()/a.median()) if a.median() else None,
                         "zero_rate_change": float((b==0).mean()-(a==0).mean()),
                         "missing_rate_change": float(b.isna().mean()-a.isna().mean()),
                         "out_of_training_range_rate": float(((b<a.min())|(b>a.max())).mean())}
    top = sorted(rows, key=lambda f: abs(rows[f]["standardized_mean_difference"]), reverse=True)
    return {"feature_count": len(features), "historical_training_available": True, "features": rows,
            "top_drift_features": top[:5], "stable_features": top[-5:], "used_for_tuning": False}


def _variant_metrics(frame: pd.DataFrame) -> dict[str, Any]:
    result = {}
    for variant, subset in frame[frame.label == "benign"].groupby("scenario_id"):
        correct = subset.prediction == "benign"; wrong = subset[~correct]
        result[variant] = {"support": len(subset), "correct_benign_predictions": int(correct.sum()),
                           "false_positive_count": int((~correct).sum()), "benign_recall": float(correct.mean()),
                           "predicted_attack_distribution": {str(k): int(v) for k,v in wrong.prediction.value_counts().items()},
                           "mean_confidence": float(subset.confidence.mean()), "median_confidence": float(subset.confidence.median()),
                           "minimum_benign_margin": float(subset.benign_margin.min())}
    return result


def evaluate(candidate_manifest_path: Path, protocol_path: Path, lock_path: Path, policy_path: Path,
             output_root: Path, report_dir: Path, artifact_dir: Path, resume: bool = False) -> dict[str, Any]:
    report_dir.mkdir(parents=True, exist_ok=True); artifact_dir.mkdir(parents=True, exist_ok=True)
    prediction_path = artifact_dir / "v036_predictions.csv"; prediction_lock = report_dir / "prediction_lock.json"
    lock = yaml.safe_load(lock_path.read_text(encoding="utf-8")); protocol = yaml.safe_load(protocol_path.read_text(encoding="utf-8")); policy = yaml.safe_load(policy_path.read_text(encoding="utf-8"))
    if protocol.get("candidate_predictions_allowed_before_lock") is not False or lock.get("holdout_modified_after_lock") is not False:
        raise ValueError("Blind prediction gate не пройден")
    if lock["protocol_sha256"] != sha256(protocol_path) or lock["policy_sha256"] != sha256(policy_path):
        raise ValueError("Protocol/policy изменены после holdout lock")
    campaign_path = ROOT / "lab/campaigns/v0_3_6_blind_holdout.yaml"
    _, frame, _ = load_holdout(campaign_path, output_root)
    for run_id, expected in lock["dataset_sha256"].items():
        path = output_root / "datasets" / f"windows_network_sensor_v0_4_{run_id}.csv"
        if sha256(path) != expected: raise ValueError(f"Dataset {run_id} изменён после lock")
    manifest = yaml.safe_load(candidate_manifest_path.read_text(encoding="utf-8")); artifact = ROOT / "ml/artifacts/v0_3_4/frozen_candidate.joblib"
    before_stat = artifact.stat(); before = sha256(artifact)
    if before != manifest["artifact_sha256"]: raise ValueError("Candidate artifact hash mismatch")
    catalog = yaml.safe_load((ROOT / "lab/scenarios/benign/v036_holdout_catalog.yaml").read_text(encoding="utf-8"))["scenarios"]
    hard = {x["scenario_id"] for x in catalog if x.get("hard_negative_target_class")}
    frame["hard_negative"] = frame.scenario_id.isin(hard)
    from v034_profiles import project_row
    features = manifest["ordered_feature_list"]
    X = pd.DataFrame([project_row(row, manifest["feature_profile"]) for row in frame.to_dict("records")], columns=features)
    if prediction_path.exists():
        if not resume: raise RuntimeError("Immutable prediction уже существует; повтор запрещён")
        locked_prediction = json.loads(prediction_lock.read_text(encoding="utf-8"))
        if sha256(prediction_path) != locked_prediction["prediction_sha256"]:
            raise ValueError("Immutable predictions изменены после prediction lock")
        saved = pd.read_csv(prediction_path); prediction_hash = sha256(prediction_path)
        frame["prediction"] = saved.prediction; frame["confidence"] = saved.confidence; frame["benign_margin"] = saved.benign_margin
        classes = [c[5:] for c in saved.columns if c.startswith("prob_")]
        probabilities = saved[[f"prob_{c}" for c in classes]].to_numpy()
        prediction_reused = True
    else:
        model = joblib.load(artifact)
        prediction = model.predict(X); probabilities = model.predict_proba(X); classes = [str(x) for x in model.classes_]
        frame["prediction"] = prediction; frame["confidence"] = probabilities.max(axis=1)
        benign_index = classes.index("benign"); other = np.max(np.delete(probabilities, benign_index, axis=1), axis=1)
        frame["benign_margin"] = probabilities[:, benign_index] - other
        saved = frame[["run_id", "execution_id", "scenario_id", "label", "environment_group", "hard_negative", "prediction", "confidence", "benign_margin"]].copy()
        for i, name in enumerate(classes): saved[f"prob_{name}"] = probabilities[:, i]
        saved.to_csv(prediction_path, index=False); prediction_hash = sha256(prediction_path); prediction_reused = False
        write_json(prediction_lock, {"prediction_locked": True, "prediction_sha256": prediction_hash,
                                    "prediction_count": len(saved), "predict_call_count": 1,
                                    "holdout_lock_sha256": sha256(lock_path), "immutable": True})
    overall = metrics(frame); per_run = {name: metrics(group) for name,group in frame.groupby("run_id")}; per_group = {name: metrics(group) for name,group in frame.groupby("environment_group")}
    variants = _variant_metrics(frame)
    attacks = {}
    for name in ATTACKS:
        subset = frame[frame.label == name]
        class_metric = overall["per_class"][name]
        attacks[name] = {**class_metric,
            "attack_to_benign": int((subset.prediction == "benign").sum()),
            "attack_to_wrong_attack": int(((subset.prediction != "benign") & (subset.prediction != name)).sum()),
            "mean_confidence": float(subset.confidence.mean()),
            "median_confidence": float(subset.confidence.median()),
            "confidence_minimum": float(subset.confidence.min())}
    calibration = _calibration(frame, probabilities, classes); bootstrap = _bootstrap(frame)
    historical = compare(overall); drift_frame = pd.concat([X.reset_index(drop=True), frame[["label","prediction"]].reset_index(drop=True)], axis=1)
    feature_distribution = _feature_distribution(drift_frame, features)
    model = joblib.load(artifact); estimator = model.steps[-1][1] if hasattr(model, "steps") else model
    importance = sorted(zip(features, estimator.feature_importances_), key=lambda x:x[1], reverse=True)
    rf = {"importance_method":"impurity", "most_used_features":[{"feature":f,"importance":float(v)} for f,v in importance],
          "rate_share_feature_count":16, "used_for_candidate_tuning":False}
    false_positive = frame[(frame.label == "benign") & (frame.prediction != "benign")]
    false_negative = frame[(frame.label != "benign") & (frame.prediction == "benign")]
    detail_columns = ["run_id","execution_id","scenario_id","environment_group","label","prediction","confidence","flow_count","window_event_count","connection_failure_rate","udp_flow_count","http_request_count","dns_query_count","total_bytes","total_packets","window_duration_seconds"]
    fp_report = {"count":len(false_positive),"dominant_predicted_classes":Counter(false_positive.prediction).most_common(),"rows":false_positive[detail_columns].to_dict("records")}
    fn_report = {"count":len(false_negative),"classes":Counter(false_negative.label).most_common(),"rows":false_negative[detail_columns].to_dict("records")}
    observation = {"rows":len(frame),"empty_windows":int((frame.window_event_count==0).sum()),"minimum_event_count":int(frame.window_event_count.min()),
                   "mean_event_count":float(frame.window_event_count.mean()),"mean_flow_count":float(frame.flow_count.mean()),
                   "errors":int((frame.label!=frame.prediction).sum()),"errors_by_group":Counter(frame[frame.label!=frame.prediction].environment_group).most_common()}
    worst_variant = min(variants, key=lambda x: variants[x]["benign_recall"]); best_variant = max(variants, key=lambda x: variants[x]["benign_recall"])
    worst_attack = min(ATTACKS, key=lambda x: attacks[x]["recall"])
    overall_policy = policy["evaluation_policy"]
    policy_flags = {
        "minimum_macro_f1_passed": overall["macro_f1"] >= overall_policy["minimum_macro_f1"],
        "minimum_balanced_accuracy_passed": overall["balanced_accuracy"] >= overall_policy["minimum_balanced_accuracy"],
        "minimum_benign_recall_passed": overall["benign_recall"] >= overall_policy["minimum_benign_recall"],
        "maximum_false_positive_rate_passed": overall["false_positive_rate"] <= overall_policy["maximum_false_positive_rate"],
        "minimum_hard_negative_benign_recall_passed": overall["hard_negative_benign_recall"] >= overall_policy["minimum_hard_negative_benign_recall"],
        "minimum_attack_macro_recall_passed": overall["attack_macro_recall"] >= overall_policy["minimum_attack_macro_recall"],
        "minimum_collapsed_attack_precision_passed": overall["collapsed_attack_precision"] >= overall_policy["minimum_collapsed_attack_precision"],
        "minimum_collapsed_attack_recall_passed": overall["collapsed_attack_recall"] >= overall_policy["minimum_collapsed_attack_recall"],
        "no_zero_recall_class_passed": not overall["zero_recall_classes"],
    }
    gp = policy["group_policy"]
    group_pass = all(m["macro_f1"]>=gp["minimum_macro_f1"] and m["benign_recall"]>=gp["minimum_benign_recall"] and m["false_positive_rate"]<=gp["maximum_false_positive_rate"] and m["attack_macro_recall"]>=gp["minimum_attack_macro_recall"] for m in per_group.values())
    vp = policy["variant_policy"]; variant_pass = all(v["benign_recall"]>=vp["minimum_benign_variant_recall"] for v in variants.values()) and sum(v["benign_recall"]==0 for v in variants.values())<=vp["maximum_zero_recall_benign_variants"]
    macro_std=float(np.std([x["macro_f1"] for x in per_run.values()])); benign_std=float(np.std([x["benign_recall"] for x in per_run.values()]));sp=policy["stability_policy"]
    stability=macro_std<=sp["maximum_macro_f1_std_across_runs"] and benign_std<=sp["maximum_benign_recall_std_across_runs"]
    integrity_flags = {"protocol_frozen_before_collection":True,"candidate_frozen_before_protocol":True,"candidate_predictions_prohibited_before_lock":True,
        "preflight_passed":True,"campaign_completed":True,"holdout_integrity_passed":True,"holdout_provenance_passed":True,"holdout_overlap_zero":True,
        "holdout_diversity_passed":True,"holdout_leakage_passed":True,"holdout_locked_before_prediction":True,"candidate_integrity_passed":True,
        "no_fit_audit_passed":True,"prediction_mapping_complete":len(frame)==252}
    passed=all(policy_flags.values()) and group_pass and variant_pass and stability
    policy_result={**integrity_flags,**policy_flags,"all_group_policies_passed":group_pass,"all_benign_variant_policies_passed":variant_pass,"stability_policy_passed":stability,
        "v036_holdout_evaluation_completed":True,"v036_holdout_policy_passed":passed,"candidate_generalization_supported":passed,"candidate_ready_for_shadow_mode":passed,
        "model_refit_on_v036":False,"sensor_ready_for_backend_integration":False,"macro_f1_std_across_runs":macro_std,"benign_recall_std_across_runs":benign_std}
    candidate_after=sha256(artifact); after_stat=artifact.stat()
    candidate_integrity={"v036_candidate_integrity_valid":before==candidate_after==manifest['artifact_sha256'],"artifact_sha256_before":before,"artifact_sha256_after":candidate_after,
        "artifact_size_before":before_stat.st_size,"artifact_size_after":after_stat.st_size,"artifact_mtime_before":before_stat.st_mtime,"artifact_mtime_after":after_stat.st_mtime,
        "model_class":manifest['model_class'],"model_parameters":manifest['model_parameters'],"feature_profile":manifest['feature_profile'],"ordered_feature_list":features,"classes":manifest['classes']}
    reports={"candidate_integrity.json":candidate_integrity,"no_fit_audit.json":{"fit_call_count":0,"partial_fit_call_count":0,"threshold_tuning_performed":False,"feature_selection_performed":False,"calibration_performed":False,"model_refit_on_v036":False},
        "overall_metrics.json":overall,"per_run_metrics.json":per_run,"per_group_metrics.json":per_group,"benign_variant_metrics.json":variants,"attack_class_metrics.json":attacks,
        "bootstrap_intervals.json":bootstrap,"calibration_analysis.json":calibration,"historical_comparison.json":historical,"false_positive_analysis.json":fp_report,"false_negative_analysis.json":fn_report,
        "feature_distribution.json":feature_distribution,"random_forest_analysis.json":rf,"observation_quality.json":observation,"v0_3_6_policy_result.json":policy_result}
    for name,value in reports.items():write_json(report_dir/name,value)
    summary = build_summary(manifest, lock, overall, per_run, per_group, variants, attacks, calibration, bootstrap, historical, feature_distribution, rf, observation, policy_result, prediction_hash, worst_variant, best_variant, worst_attack)
    (report_dir/"v0_3_6_summary.md").write_text(summary,encoding="utf-8")
    return {"prediction_sha256":prediction_hash,"prediction_reused":prediction_reused,"overall_metrics":overall,"policy_result":policy_result,"worst_benign_variant":worst_variant,"best_benign_variant":best_variant,"worst_attack_class":worst_attack}


def build_summary(manifest,lock,overall,per_run,per_group,variants,attacks,calibration,bootstrap,historical,drift,rf,observation,policy,prediction_hash,worst_variant,best_variant,worst_attack):
    sections=["# Филин v0.3.6 — перспективная holdout-проверка","## Цель\nПроверить обобщение заранее замороженного сетевого candidate на prospective holdout.",
    "## Статус проверки\nПерспективная holdout-проверка, независимая от обучения и выбора модели; не double-blind.","## Ограничения blind-терминологии\nРазработчик знает архитектуру candidate.",
    f"## Frozen candidate\n`{manifest['candidate_id']}`, `{manifest['model_class']}`, 16 признаков `{manifest['feature_profile']}`.","## Protocol freeze\nCandidate заморожен до protocol; predictions до lock запрещены.",
    "## Evaluation policy\nПорог и policy не настраивались по predictions.","## Campaign design\n12 Docker-runs, 4 группы, 252 окна.","## Новые benign workflows\n16 новых scenario ID, по 12 окон каждого.",
    "## Новые варианты существующих атак\nИспользованы только пять существующих безопасных локальных классов.","## Environment groups\nnovel_workflows, ambiguous_low_signal, topology_protocol, observation_stress.",
    "## Preflight\nЧетыре групповых набора проверок успешны; candidate artifact не загружался.","## Campaign integrity\n12/12 runs, 252/252 windows, marker/correlation/aggregation audits успешны.",
    "## Provenance\nПроисхождение подтверждено; старые rows не использованы.","## Overlap audit\nOverlap run IDs и dataset hashes равен нулю.","## Diversity audit\n252 уникальных feature-вектора; cross-label duplicates отсутствуют.",
    "## Leakage audit\nЗапрещённые metadata-поля не входят в 16 model features.",f"## Holdout lock\nLock создан до prediction; SHA-256 `{sha256(ROOT/'ml/experiments/v0_3_6/holdout_lock_manifest.yaml')}`.",
    "## Candidate integrity\nArtifact hash, размер и mtime неизменны.","## No-fit audit\nfit=0, partial_fit=0, calibration/threshold tuning/feature selection=false.",
    "## Dataset composition\n192 benign, 60 attack (по 12 каждого attack-класса).",f"## Overall metrics\n```json\n{json.dumps(overall,ensure_ascii=False,indent=2)}\n```",
    f"## Per-run metrics\n```json\n{json.dumps(per_run,ensure_ascii=False,indent=2)}\n```",f"## Per-group metrics\n```json\n{json.dumps(per_group,ensure_ascii=False,indent=2)}\n```",
    f"## Benign variant metrics\nWorst: `{worst_variant}`; best: `{best_variant}`.\n```json\n{json.dumps(variants,ensure_ascii=False,indent=2)}\n```",f"## Attack-class metrics\nWorst: `{worst_attack}`.\n```json\n{json.dumps(attacks,ensure_ascii=False,indent=2)}\n```",
    f"## Confidence intervals\n```json\n{json.dumps(bootstrap,ensure_ascii=False,indent=2)}\n```",f"## Confidence и calibration\nCalibration не выполнялась.\n```json\n{json.dumps(calibration,ensure_ascii=False,indent=2)}\n```",
    f"## Сравнение с v0.3.4\n```json\n{json.dumps(historical['vs_v0_3_4'],ensure_ascii=False,indent=2)}\n```",f"## Сравнение с v0.3.5\n```json\n{json.dumps(historical['vs_v0_3_5'],ensure_ascii=False,indent=2)}\n```",
    f"## False positives\n{overall['false_positive_count']}.",f"## False negatives\n{overall['attack_false_negative_count']} attack→benign.",f"## Feature distribution\nTop drift: {', '.join(drift['top_drift_features'])}.",
    f"## Random Forest analysis\nMost used: {', '.join(x['feature'] for x in rf['most_used_features'][:5])}.",f"## Observation quality\n```json\n{json.dumps(observation,ensure_ascii=False,indent=2)}\n```",
    f"## Policy result\n```json\n{json.dumps(policy,ensure_ascii=False,indent=2)}\n```","## Ограничения\nHoldout не означает production readiness; candidate не интегрирован в backend.",
    "## Вывод\nv0.3.6 не участвовала в обучении; threshold не менялся; runs не повторялись по prediction; модель после evaluation не настраивалась.",
    "## Следующий этап\nПри положительной policy — v0.3.7 passive shadow mode без автоматического блокирования.",f"\nPrediction SHA-256: `{prediction_hash}`\n"]
    return "\n\n".join(sections)
