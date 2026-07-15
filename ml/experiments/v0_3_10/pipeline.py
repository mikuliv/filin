"""Общие операции class-conditional evidence pipeline v0.3.10."""
from __future__ import annotations

import hashlib
import json
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (accuracy_score, balanced_accuracy_score, brier_score_loss,
                             confusion_matrix, f1_score, log_loss, precision_recall_fscore_support,
                             precision_score, recall_score)
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / "ml/features"), str(ROOT / "ml/models"), str(ROOT / "ml/decision")]

from continuous_class_support import ContinuousClassSupport
from group_aware_sigmoid_calibration import GroupAwareSigmoidCalibrator
from mondrian_conformal_classifier import MondrianConformalClassifier
from network_sensor_v0_6 import (CONTROL_PROFILE, EVIDENCE_PROFILE, build_causal_frame,
                                 ordered_features, schema_sha256)
from v0310_minimal_promotion import ATTACK_CLASSES, MinimalPromotionDecision, MinimalPromotionPolicy
from v0310_activity_key_audit import activity_state_key

# Совместимые заглушки не участвуют в новом minimal decision path.
EvidenceThresholds = build_evidence_record = AlertLifecycle = None


CLASSES = ["benign", *ATTACK_CLASSES]
PROFILES = [CONTROL_PROFILE]
GATES = ["hist_gradient_boosting"]
SUBTYPES = ["hist_gradient_boosting"]


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sha256_json(value) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, default=_json_default), encoding="utf-8")


def _json_default(value):
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return float(value)
    if isinstance(value, np.ndarray):
        return value.tolist()
    raise TypeError(type(value).__name__)


def make_gate(name: str):
    if name == "logistic_regression":
        estimator = LogisticRegression(C=1.0, class_weight="balanced", max_iter=2000, random_state=42)
        return Pipeline([("imputer", SimpleImputer(strategy="median")), ("scaler", StandardScaler()), ("model", estimator)])
    if name == "random_forest":
        estimator = RandomForestClassifier(n_estimators=300, max_depth=6, min_samples_leaf=2, class_weight="balanced_subsample", random_state=42, n_jobs=-1)
    elif name == "hist_gradient_boosting":
        estimator = HistGradientBoostingClassifier(learning_rate=.05, max_iter=200, max_leaf_nodes=15, l2_regularization=1.0, random_state=42)
    else:
        raise KeyError(name)
    return Pipeline([("imputer", SimpleImputer(strategy="median")), ("model", estimator)])


def make_subtype(name: str):
    if name == "random_forest":
        estimator = RandomForestClassifier(n_estimators=300, max_depth=6, min_samples_leaf=2, class_weight="balanced_subsample", random_state=42, n_jobs=-1)
    elif name == "hist_gradient_boosting":
        estimator = HistGradientBoostingClassifier(learning_rate=.05, max_iter=200, max_leaf_nodes=15, l2_regularization=1.0, random_state=42)
    else:
        raise KeyError(name)
    return Pipeline([("imputer", SimpleImputer(strategy="median")), ("model", estimator)])


def model_parameters(name: str) -> dict:
    if name == "logistic_regression":
        return {"C": 1.0, "class_weight": "balanced", "max_iter": 2000, "random_state": 42}
    if name == "random_forest":
        return {"n_estimators": 300, "max_depth": 6, "min_samples_leaf": 2, "class_weight": "balanced_subsample", "random_state": 42, "n_jobs": -1}
    return {"learning_rate": .05, "max_iter": 200, "max_leaf_nodes": 15, "l2_regularization": 1.0, "random_state": 42}


def aligned_probabilities(model, X, classes: list[str]) -> np.ndarray:
    raw = model.predict_proba(X)
    model_classes = [str(value) for value in model.classes_]
    result = np.zeros((len(X), len(classes)), dtype=float)
    for index, label in enumerate(classes):
        if label in model_classes:
            result[:, index] = raw[:, model_classes.index(label)]
    row_sum = result.sum(axis=1, keepdims=True)
    return np.divide(result, row_sum, out=np.zeros_like(result), where=row_sum > 0)


def joint_probabilities(gate_probability, subtype_probability) -> np.ndarray:
    gate = np.asarray(gate_probability, dtype=float).reshape(-1)
    subtype = np.asarray(subtype_probability, dtype=float)
    if len(gate) != len(subtype) or subtype.shape[1] != len(ATTACK_CLASSES):
        raise ValueError("Несогласованные gate/subtype probabilities")
    result = np.column_stack([1.0 - gate, gate[:, None] * subtype])
    if not np.isfinite(result).all() or (result < -1e-12).any() or (result > 1 + 1e-12).any():
        raise ValueError("Joint probabilities должны быть конечными и принадлежать [0,1]")
    if not np.allclose(result.sum(axis=1), 1.0, atol=1e-8):
        raise ValueError("Сумма joint probabilities должна быть равна 1")
    return result


def expected_calibration_error(y_true, probabilities, bins: int = 10) -> float:
    matrix = np.asarray(probabilities, dtype=float)
    confidence = matrix.max(axis=1)
    prediction = matrix.argmax(axis=1)
    truth = np.asarray(y_true, dtype=int)
    total = len(truth)
    result = 0.0
    for left in np.linspace(0, 1, bins + 1)[:-1]:
        right = left + 1 / bins
        mask = (confidence > left) & (confidence <= right)
        if mask.any():
            result += mask.sum() / total * abs((prediction[mask] == truth[mask]).mean() - confidence[mask].mean())
    return float(result)


def closed_set_metrics(labels, probabilities) -> dict:
    labels = np.asarray(labels, dtype=str)
    prediction = np.asarray(CLASSES, dtype=object)[np.asarray(probabilities).argmax(axis=1)]
    benign = labels == "benign"
    pred_benign = prediction == "benign"
    precision, recall, f1, support = precision_recall_fscore_support(labels, prediction, labels=CLASSES, zero_division=0)
    per_class = {label: {"precision": float(precision[i]), "recall": float(recall[i]), "f1": float(f1[i]), "support": int(support[i])} for i, label in enumerate(CLASSES)}
    return {
        "accuracy": float(accuracy_score(labels, prediction)),
        "balanced_accuracy": float(balanced_accuracy_score(labels, prediction)),
        "macro_precision": float(precision_score(labels, prediction, average="macro", zero_division=0)),
        "macro_recall": float(recall_score(labels, prediction, average="macro", zero_division=0)),
        "macro_f1": float(f1_score(labels, prediction, average="macro", zero_division=0)),
        "weighted_f1": float(f1_score(labels, prediction, average="weighted", zero_division=0)),
        "benign_precision": float(per_class["benign"]["precision"]),
        "benign_recall": float(per_class["benign"]["recall"]),
        "benign_f1": float(per_class["benign"]["f1"]),
        "FPR": float((~pred_benign[benign]).mean()) if benign.any() else 0.0,
        "attack_macro_precision": float(np.mean([per_class[name]["precision"] for name in ATTACK_CLASSES])),
        "attack_macro_recall": float(np.mean([per_class[name]["recall"] for name in ATTACK_CLASSES])),
        "attack_macro_f1": float(np.mean([per_class[name]["f1"] for name in ATTACK_CLASSES])),
        "per_class": per_class,
        "confusion_matrix": confusion_matrix(labels, prediction, labels=CLASSES).tolist(),
        "zero_recall_classes": [name for name in CLASSES if per_class[name]["support"] and per_class[name]["recall"] == 0],
    }


def build_feature_frame(all_rows: pd.DataFrame, profile: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    # Dataset builder сохраняет execution order строками, но намеренно не
    # экспортирует служебный run_sequence как потенциальный leakage field.
    ordered = all_rows.reset_index(drop=True).copy()
    ordered["_causal_row_order"] = np.arange(len(ordered))
    ordered = ordered.sort_values(["run_id", "_causal_row_order"]).drop(columns="_causal_row_order").reset_index(drop=True)
    features = build_causal_frame(ordered.to_dict("records"), profile, history_depth=6)
    scored = ~ordered["warmup"].astype(bool)
    return ordered.loc[scored].reset_index(drop=True), features.loc[scored].reset_index(drop=True)


def attach_manifest_timestamps(rows: pd.DataFrame, output_root: Path) -> pd.DataFrame:
    """Присоединить заранее запланированное observable time по execution_id.

    Episode metadata не используется: timestamp берётся только из immutable
    scenario manifest и нужен lifecycle для причинного inactivity reset.
    """
    frame = rows.drop(columns=["planned_started_at"], errors="ignore").copy()
    mappings = []
    for run_id in frame["run_id"].astype(str).drop_duplicates():
        path = output_root / "runs" / run_id / "scenario_manifest.yaml"
        payload = __import__("yaml").safe_load(path.read_text(encoding="utf-8"))
        mappings.extend({"execution_id": item["execution_id"], "planned_started_at": item["planned_started_at"]}
                        for item in payload["scenarios"])
    mapping = pd.DataFrame(mappings).drop_duplicates("execution_id")
    result = frame.merge(mapping, on="execution_id", how="left", validate="many_to_one", sort=False)
    if result["planned_started_at"].isna().any() or len(result) != len(frame):
        raise ValueError("Неполное timestamp mapping из immutable scenario manifests")
    return result


def oof_base(rows: pd.DataFrame, X: pd.DataFrame, gate_name: str, subtype_name: str) -> dict:
    labels = rows["episode_class"].astype(str).to_numpy()
    binary = (labels != "benign").astype(int)
    groups = rows["run_id"].astype(str).to_numpy()
    gate_oof = np.zeros(len(rows), dtype=float)
    subtype_oof = np.zeros((len(rows), len(ATTACK_CLASSES)), dtype=float)
    outer = StratifiedGroupKFold(n_splits=6, shuffle=True, random_state=42)
    fold_audit = []
    for fold, (train, test) in enumerate(outer.split(X, labels, groups), 1):
        if set(groups[train]) & set(groups[test]):
            raise RuntimeError("Run пересёк outer fold")
        gate = make_gate(gate_name).fit(X.iloc[train], binary[train])
        gate_oof[test] = aligned_probabilities(gate, X.iloc[test], ["0", "1"])[:, 1]
        attack_train = train[binary[train] == 1]
        subtype = make_subtype(subtype_name).fit(X.iloc[attack_train], labels[attack_train])
        subtype_oof[test] = aligned_probabilities(subtype, X.iloc[test], ATTACK_CLASSES)
        inner_groups = groups[train]
        inner_labels = labels[train]
        inner = StratifiedGroupKFold(n_splits=4, shuffle=True, random_state=42)
        inner_audit = []
        for inner_fold, (inner_train, inner_test) in enumerate(inner.split(X.iloc[train], inner_labels, inner_groups), 1):
            if set(inner_groups[inner_train]) & set(inner_groups[inner_test]):
                raise RuntimeError("Run пересёк inner fold")
            inner_audit.append({"fold": inner_fold, "train_runs": sorted(set(inner_groups[inner_train])), "test_runs": sorted(set(inner_groups[inner_test]))})
        fold_audit.append({"fold": fold, "train_runs": sorted(set(groups[train])), "test_runs": sorted(set(groups[test])), "inner": inner_audit})
    joint = joint_probabilities(gate_oof, subtype_oof)
    truth_index = np.array([CLASSES.index(label) for label in labels])
    metrics = closed_set_metrics(labels, joint)
    metrics["ECE"] = expected_calibration_error(truth_index, joint)
    return {"gate_oof": gate_oof, "subtype_oof": subtype_oof, "joint_oof": joint, "metrics": metrics, "fold_audit": fold_audit}


def base_gate_flags(metrics: dict) -> dict:
    return {
        "closed_set_macro_f1": metrics["macro_f1"] >= .85,
        "closed_set_benign_recall": metrics["benign_recall"] >= .88,
        "closed_set_FPR": metrics["FPR"] <= .12,
        "closed_set_attack_macro_recall": metrics["attack_macro_recall"] >= .90,
        "zero_recall_attack_classes": not any(name in ATTACK_CLASSES for name in metrics["zero_recall_classes"]),
    }


def calibrated_joint(gate_calibrator, subtype_calibrator, gate_probability, subtype_probability) -> np.ndarray:
    gate = gate_calibrator.predict_proba(np.asarray(gate_probability))[:, list(gate_calibrator.model.classes_).index(1)]
    subtype_raw = subtype_calibrator.predict_proba(np.asarray(subtype_probability))
    subtype = np.zeros((len(subtype_raw), len(ATTACK_CLASSES)))
    for index, label in enumerate(ATTACK_CLASSES):
        if label in list(subtype_calibrator.model.classes_):
            subtype[:, index] = subtype_raw[:, list(subtype_calibrator.model.classes_).index(label)]
    return joint_probabilities(gate, subtype)


def evidence_decisions(rows: pd.DataFrame, probabilities: np.ndarray, conformal, support, X: pd.DataFrame, parameters: dict) -> pd.DataFrame:
    """Преобразовать immutable probabilities в причинные lifecycle decisions."""
    p_values=conformal.p_values(probabilities);conformal_sets=conformal.predict_set(probabilities);support_rows=support.transform(X)
    thresholds=EvidenceThresholds(parameters["strong_attack_probability"],parameters["strong_probability_margin"],
        parameters["strong_support_ratio"],parameters["maximum_strong_benign_probability"],parameters["weak_attack_probability"],
        parameters["strong_benign_reset_probability"])
    lifecycle=AlertLifecycle(decay=parameters["decay"],activation_threshold=parameters["activation_threshold"],
        weak_repeat_policy=parameters["weak_repeat_policy"],active_minimum_hold_windows=2,state_ttl_windows=3)
    records=[];last_run=None
    for index,row in rows.reset_index(drop=True).iterrows():
        if last_run is not None and row["run_id"]!=last_run:lifecycle.reset_run()
        last_run=row["run_id"];probability_map=dict(zip(CLASSES,map(float,probabilities[index])));p_map=dict(zip(CLASSES,map(float,p_values[index])))
        record=build_evidence_record(timestamp=row["planned_started_at"],asset_state_key=str(row["run_id"]),probabilities=probability_map,
            conformal_set=conformal_sets[index],conformal_p_values=p_map,support=support_rows[index],thresholds=thresholds)
        transition=lifecycle.update(record);record.update(transition);record["support_result"]=support_rows[index];records.append(record)
    return pd.DataFrame(records)


def operational_metrics(rows: pd.DataFrame, decisions: pd.DataFrame) -> tuple[dict, dict]:
    labels = rows["episode_class"].astype(str).to_numpy()
    states = decisions["final_decision"].astype(str).to_numpy()
    benign = labels == "benign"
    attack = ~benign
    alerts=np.array([value.startswith("active:") for value in states]);high=np.array([value.startswith("active:") and value!="active:unclassified" for value in states]);review=np.array([value.startswith("review:") for value in states]);benign_prediction=np.array([value=="observing" for value in states])
    evidence=np.array([bool(row.strong_attack_evidence or row.weak_attack_evidence or (row.top_class in ATTACK_CLASSES and row.top_class in row.conformal_set and row.support_ranks[row.top_class]<=2)) for row in decisions.itertuples()])
    window = {
        "benign_recall": float(benign_prediction[benign].mean()) if benign.any() else 0.0,
        "false_positive_count": int(alerts[benign].sum()),
        "false_positive_rate": float(alerts[benign].mean()) if benign.any() else 0.0,
        "high_severity_false_positive_count": int(high[benign].sum()),
        "high_severity_FPR": float(high[benign].mean()) if benign.any() else 0.0,
        "true_class_evidence_window_recall": float(evidence[attack].mean()) if attack.any() else 0.0,
        "final_attack_window_alert_rate": float(alerts[attack].mean()) if attack.any() else 0.0,
        "attack_to_benign_FN_count": int(benign_prediction[attack].sum()),
        "attack_to_benign_FN_rate": float(benign_prediction[attack].mean()) if attack.any() else 0.0,
        "attack_review_count": int(review[attack].sum()),
        "attack_review_rate": float(review[attack].mean()) if attack.any() else 0.0,
        "review_required_count": int(review.sum()),
        "review_rate": float(review.mean()),
        "review_novel_rate": float((states == "review:novel").mean()),
        "review_ambiguous_rate": float((states == "review:ambiguous").mean()),
        "review_weak_evidence_rate": float((states == "review:weak").mean()),
        "suspicious_unclassified_rate": float((states == "active:unclassified").mean()),
        "decision_coverage": float((~review).mean()),
        "post_activation_alert_persistence": _persistence(rows,alerts),
    }
    episodes = []
    for episode_id, group in rows.reset_index(drop=True).groupby("episode_id", sort=False):
        indexes = group.index.to_numpy()
        label = str(group.iloc[0]["episode_class"])
        episode_alerts = alerts[indexes]
        episode_high = high[indexes]
        episodes.append({"episode_id": episode_id, "class": label, "alert": bool(episode_alerts.any()),
            "high": bool(episode_high.any()), "first_alert": int(np.argmax(episode_alerts) + 1) if episode_alerts.any() else None})
    ep = pd.DataFrame(episodes)
    benign_ep, attack_ep = ep[ep["class"] == "benign"], ep[ep["class"] != "benign"]
    alerted = ep[ep["alert"]]
    true_alerts = int((alerted["class"] != "benign").sum())
    delays = [int(value) for value in attack_ep.loc[attack_ep["alert"], "first_alert"].dropna()]
    per_class = {}
    for label in ATTACK_CLASSES:
        subset = attack_ep[attack_ep["class"] == label]
        per_class[label] = {"support": len(subset), "recall": float(subset["alert"].mean()) if len(subset) else 0.0,
            "precision": float((alerted["class"] == label).sum() / max(len(alerted), 1)),
            "median_time_to_alert": float(np.median(subset.loc[subset["alert"], "first_alert"])) if subset["alert"].any() else None}
    episode = {
        "benign_episode_support": len(benign_ep), "attack_episode_support": len(attack_ep),
        "benign_episode_false_alert_count": int(benign_ep["alert"].sum()),
        "benign_episode_false_alert_rate": float(benign_ep["alert"].mean()) if len(benign_ep) else 0.0,
        "benign_episode_high_severity_alert_count": int(benign_ep["high"].sum()),
        "benign_episode_high_severity_alert_rate": float(benign_ep["high"].mean()) if len(benign_ep) else 0.0,
        "attack_episode_detected_count": int(attack_ep["alert"].sum()),
        "attack_episode_recall": float(attack_ep["alert"].mean()) if len(attack_ep) else 0.0,
        "attack_episode_unresolved_count": int((~attack_ep["alert"]).sum()),
        "attack_episode_unresolved_rate": float((~attack_ep["alert"]).mean()) if len(attack_ep) else 0.0,
        "episode_alert_precision": float(true_alerts / max(len(alerted), 1)),
        "detection_by_first_window": float((attack_ep["first_alert"]<=1).mean()),
        "detection_by_second_window": float((attack_ep["first_alert"]<=2).mean()),
        "detection_by_third_window": float((attack_ep["first_alert"]<=3).mean()),
        "time_to_first_alert": {"mean": float(np.mean(delays)) if delays else None, "median": float(np.median(delays)) if delays else None, "maximum": max(delays) if delays else None, "standard_deviation": float(np.std(delays)) if delays else None},
        "per_class": per_class,
        "zero_recall_attack_episode_classes": [name for name, value in per_class.items() if value["support"] and value["recall"] == 0],
    }
    return window, episode


def _persistence(rows,alerts):
    values=[]
    for _,indices in rows.reset_index(drop=True).groupby("episode_id",sort=False).groups.items():
        seq=list(indices);seen=False
        for idx in seq:
            if alerts[idx]:seen=True
            if seen:values.append(bool(alerts[idx]))
    return float(np.mean(values)) if values else 1.0


def conformal_metrics(labels, sets: list[list[str]]) -> dict:
    labels = np.asarray(labels, dtype=str)
    sizes = np.array([len(value) for value in sets])
    covered = np.array([label in value for label, value in zip(labels, sets)])
    return {
        "empirical_coverage_overall": float(covered.mean()),
        "coverage_per_class": {label: float(covered[labels == label].mean()) for label in CLASSES},
        "average_prediction_set_size": float(sizes.mean()),
        "median_prediction_set_size": float(np.median(sizes)),
        "singleton_set_rate": float((sizes == 1).mean()), "multi_class_set_rate": float((sizes > 1).mean()),
        "empty_set_rate": float((sizes == 0).mean()),
        "benign_included_rate": float(np.mean(["benign" in value for value in sets])),
        "true_attack_class_included_rate": float(covered[labels != "benign"].mean()),
        "wrong_only_set_rate": float((~covered & (sizes > 0)).mean()),
    }


def support_metrics(labels, results) -> dict:
    labels=np.asarray(labels,dtype=str);ranks=np.array([value.ranks[label] for label,value in zip(labels,results)]);finite=np.array([all(np.isfinite(list(value.distances.values()))) for value in results])
    agreement=np.array([value.best_class==label for label,value in zip(labels,results)]);top2=ranks<=2
    return {"true_class_support_rank_distribution":{str(rank):int((ranks==rank).sum()) for rank in range(1,len(CLASSES)+1)},
        "true_class_top1_support_rate":float((ranks==1).mean()),"true_class_top2_support_rate":float(top2.mean()),
        "probability_support_agreement":float(agreement.mean()),"no_finite_distance_count":int((~finite).sum()),"no_finite_distance_rate":float((~finite).mean()),
        "binary_support_conflict_rate":float(np.mean([sum(v<=1 for v in value.normalized_distances.values())>1 for value in results])),
        "support_rate_per_class":{label:float(top2[labels==label].mean()) for label in CLASSES},
        "class_with_weakest_top1_support":min(CLASSES,key=lambda label:float((ranks[labels==label]==1).mean())),
        "class_with_weakest_top2_support":min(CLASSES,key=lambda label:float(top2[labels==label].mean()))}


def calibration_metrics(labels, before, after) -> dict:
    truth = np.array([CLASSES.index(str(value)) for value in labels])
    onehot = np.eye(len(CLASSES))[truth]
    def block(matrix):
        return {"log_loss": float(log_loss(truth, matrix, labels=list(range(len(CLASSES))))),
            "multiclass_brier": float(np.mean(np.sum((matrix - onehot) ** 2, axis=1))),
            "ECE": expected_calibration_error(truth, matrix)}
    return {"before_frozen_calibration": block(np.asarray(before)), "after_frozen_calibration": block(np.asarray(after)), "validation_calibration_performed": False}


# Определения ниже намеренно заменяют историческую v0.3.9-реализацию выше:
# новый путь не использует support gate, signed evidence или active lifecycle.
def evidence_decisions(rows: pd.DataFrame, probabilities: np.ndarray, conformal, support, X: pd.DataFrame, parameters: dict) -> pd.DataFrame:
    conformal_sets = conformal.predict_set(probabilities)
    support_rows = support.transform(X)
    strong = parameters.get("strong_thresholds_per_class") or {label: parameters.get("strong_attack_probability", .8) for label in ATTACK_CLASSES}
    weak = parameters.get("weak_thresholds_per_class") or {label: parameters.get("weak_attack_probability", .45) for label in ATTACK_CLASSES}
    policy = MinimalPromotionPolicy(strong_thresholds_per_class=strong,
        strong_probability_margin=parameters.get("strong_probability_margin", .2),
        maximum_strong_benign_probability=parameters.get("maximum_strong_benign_probability", .2),
        weak_thresholds_per_class=weak, weak_probability_margin=parameters.get("weak_probability_margin", 0.0),
        weak_benign_ceiling=parameters.get("weak_benign_ceiling", .5),
        weak_repetition_policy=parameters.get("weak_repetition_policy", parameters.get("weak_repeat_policy", "two_of_three")),
        pending_ttl_windows=parameters.get("pending_ttl_windows", 3), ambiguity_margin=parameters.get("ambiguity_margin", .07),
        strong_benign_probability=parameters.get("strong_benign_probability", .8),
        strong_benign_margin=parameters.get("strong_benign_margin", .3), dedup_ttl_windows=parameters.get("dedup_ttl_windows", 3))
    engine = MinimalPromotionDecision(policy)
    records, last_run, sequence, previous_time, run_window = [], None, 0, None, 0
    for index, row in rows.reset_index(drop=True).iterrows():
        timestamp = pd.Timestamp(row["planned_started_at"])
        if last_run is None or row["run_id"] != last_run:
            engine.reset(); sequence = 0; run_window = 0; previous_time = None
        elif previous_time is not None and (timestamp - previous_time).total_seconds() > 120:
            sequence += 1
        last_run, previous_time, run_window = row["run_id"], timestamp, run_window + 1
        probability_map = dict(zip(CLASSES, map(float, probabilities[index])))
        key = activity_state_key(str(row["run_id"]), str(sequence))
        record = engine.decide(activity_state_key=key, window_index=run_window,
                               probabilities=probability_map, conformal_set=list(conformal_sets[index]))
        record.update({"activity_state_key": key, "top_class": CLASSES[int(np.argmax(probabilities[index]))],
                       "joint_probabilities": probability_map, "conformal_set": list(conformal_sets[index]),
                       "support_ranks": support_rows[index].ranks, "support_margins": support_rows[index].margins,
                       "support_normalized_distances": support_rows[index].normalized_distances,
                       "support_result": support_rows[index],
                       "diagnostic_support_affects_decision": False})
        records.append(record)
    return pd.DataFrame(records)


def operational_metrics(rows: pd.DataFrame, decisions: pd.DataFrame) -> tuple[dict, dict]:
    labels = rows["episode_class"].astype(str).to_numpy()
    states = decisions["final_decision"].astype(str).to_numpy()
    benign, attack = labels == "benign", labels != "benign"
    alerts = np.array([value.startswith("alert_emitted:") for value in states])
    high = np.array([value.startswith("alert_emitted:") and value != "alert_emitted:unclassified" for value in states])
    review = np.array([value.startswith("review_required:") for value in states])
    pending = np.array([value.startswith("observe_pending:") for value in states])
    benign_prediction = states == "benign"
    evidence = np.array([bool((row.strong_attack_evidence or row.weak_attack_evidence) and row.evidence_class == label)
                         for row, label in zip(decisions.itertuples(), labels)])
    window = {"benign_recall": float(benign_prediction[benign].mean()),
        "false_positive_count": int(alerts[benign].sum()), "false_positive_rate": float(alerts[benign].mean()),
        "benign_window_alert_emission_rate": float(alerts[benign].mean()),
        "high_severity_false_positive_count": int(high[benign].sum()), "high_severity_FPR": float(high[benign].mean()),
        "true_class_candidate_evidence_recall": float(evidence[attack].mean()),
        "true_class_evidence_window_recall": float(evidence[attack].mean()),
        "alert_emission_window_rate": float(alerts.mean()), "attack_alert_emission_window_rate": float(alerts[attack].mean()),
        "final_attack_window_alert_rate": float(alerts[attack].mean()),
        "attack_to_benign_FN_count": int(benign_prediction[attack].sum()), "attack_to_benign_FN_rate": float(benign_prediction[attack].mean()),
        "pending_count": int(pending.sum()), "pending_rate": float(pending.mean()),
        "attack_pending_count": int(pending[attack].sum()), "attack_pending_rate": float(pending[attack].mean()),
        "attack_review_count": int(review[attack].sum()), "attack_review_rate": float(review[attack].mean()),
        "review_required_count": int(review.sum()), "review_rate": float(review.mean()),
        "review_novel_rate": float((states == "review_required:novel").mean()),
        "review_ambiguous_rate": float((states == "review_required:ambiguous").mean()),
        "suspicious_unclassified_rate": float((states == "alert_emitted:unclassified").mean()),
        "decision_coverage": float((~review & ~pending).mean())}
    episodes = []
    for episode_id, group in rows.reset_index(drop=True).groupby("episode_id", sort=False):
        indexes = group.index.to_numpy(); label = str(group.iloc[0]["episode_class"]); episode_alerts = alerts[indexes]
        episodes.append({"episode_id": episode_id, "class": label, "alert": bool(episode_alerts.any()),
                         "high": bool(high[indexes].any()), "first_alert": int(np.argmax(episode_alerts) + 1) if episode_alerts.any() else None})
    ep = pd.DataFrame(episodes); benign_ep = ep[ep["class"] == "benign"]; attack_ep = ep[ep["class"] != "benign"]
    alerted = ep[ep["alert"]]; true_alerts = int((alerted["class"] != "benign").sum())
    delays = [int(value) for value in attack_ep.loc[attack_ep["alert"], "first_alert"].dropna()]
    per_class = {}
    for label in ATTACK_CLASSES:
        subset = attack_ep[attack_ep["class"] == label]
        per_class[label] = {"support": len(subset), "recall": float(subset["alert"].mean()),
                            "precision": float((alerted["class"] == label).sum() / max(len(alerted), 1)),
                            "median_time_to_alert": float(np.median(subset.loc[subset["alert"], "first_alert"])) if subset["alert"].any() else None}
    episode = {"benign_episode_support": len(benign_ep), "attack_episode_support": len(attack_ep),
        "benign_episode_false_alert_count": int(benign_ep["alert"].sum()), "benign_episode_false_alert_rate": float(benign_ep["alert"].mean()),
        "benign_episode_high_severity_alert_count": int(benign_ep["high"].sum()), "benign_episode_high_severity_alert_rate": float(benign_ep["high"].mean()),
        "attack_episode_detected_count": int(attack_ep["alert"].sum()), "attack_episode_recall": float(attack_ep["alert"].mean()),
        "attack_episode_unresolved_count": int((~attack_ep["alert"]).sum()), "attack_episode_unresolved_rate": float((~attack_ep["alert"]).mean()),
        "episode_alert_precision": float(true_alerts / len(alerted)) if len(alerted) else 1.0,
        "detection_by_first_window": float((attack_ep["first_alert"] <= 1).mean()),
        "detection_by_second_window": float((attack_ep["first_alert"] <= 2).mean()),
        "detection_by_third_window": float((attack_ep["first_alert"] <= 3).mean()),
        "time_to_first_alert": {"mean": float(np.mean(delays)) if delays else None, "median": float(np.median(delays)) if delays else None,
                                "maximum": max(delays) if delays else None, "standard_deviation": float(np.std(delays)) if delays else None},
        "per_class": per_class, "zero_recall_attack_episode_classes": [name for name, value in per_class.items() if value["recall"] == 0]}
    return window, episode
