"""Общие воспроизводимые операции training/validation цикла v0.3.7."""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import sys
from typing import Iterable

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import TransformedTargetRegressor
from sklearn.ensemble import HistGradientBoostingClassifier, IsolationForest, RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    brier_score_loss,
    confusion_matrix,
    f1_score,
    log_loss,
    precision_recall_fscore_support,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


ROOT = Path(__file__).resolve().parents[3]
FEATURE_DIR = ROOT / "ml" / "features"
if str(FEATURE_DIR) not in sys.path:
    sys.path.insert(0, str(FEATURE_DIR))

from network_sensor_v0_5 import (  # noqa: E402
    CONTEXTUAL_ORDER,
    CONTROL_FEATURES,
    TEMPORAL_ORDER,
    build_causal_frame,
    schema_sha,
)
from ml.decision.v037_temporal_evidence import TemporalEvidenceAccumulator  # noqa: E402
from ml.models.benign_ood_guard import BenignOODGuard  # noqa: E402
from ml.models.group_aware_sigmoid_calibration import GroupAwareSigmoidCalibrator  # noqa: E402


ATTACK_CLASSES = ["port_scan", "auth_failures", "web_probe", "low_rate_dos", "beacon_simulation"]
DECISION_STATES = ["benign", "insufficient_evidence", "suspicious_unclassified"] + [
    f"attack_candidate:{name}" for name in ATTACK_CLASSES
]
PROFILES = {
    "network_sensor_v0_4_rates_control": CONTROL_FEATURES,
    "network_sensor_v0_5_temporal": TEMPORAL_ORDER,
    "network_sensor_v0_5_contextual": CONTEXTUAL_ORDER,
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_json(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")).hexdigest()


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


def build_feature_sets(all_rows: pd.DataFrame, depths: Iterable[int] = (3, 4, 6)) -> dict[tuple[str, int], pd.DataFrame]:
    """Строит признаки последовательно внутри run, включая warm-up в causal state."""
    ordered = all_rows.sort_values(["run_id", "window_index"], kind="stable").reset_index(drop=True)
    result: dict[tuple[str, int], pd.DataFrame] = {}
    for profile in ("network_sensor_v0_5_temporal", "network_sensor_v0_5_contextual"):
        for depth in depths:
            frames = []
            for _, run in ordered.groupby("run_id", sort=False):
                frames.append(build_causal_frame(run.to_dict("records"), profile, depth))
            result[(profile, depth)] = pd.concat(frames, ignore_index=True).astype(float)
    result[("network_sensor_v0_4_rates_control", 0)] = pd.concat(
        [build_causal_frame(run.to_dict("records"), "network_sensor_v0_4_rates_control", 4)
         for _, run in ordered.groupby("run_id", sort=False)], ignore_index=True
    ).astype(float)
    return result


def scored_rows(all_rows: pd.DataFrame) -> pd.DataFrame:
    ordered = all_rows.sort_values(["run_id", "window_index"], kind="stable").reset_index(drop=True)
    return ordered.loc[~ordered["warmup"].astype(bool)].reset_index(drop=True)


def scored_features(all_rows: pd.DataFrame, feature_sets: dict[tuple[str, int], pd.DataFrame], profile: str, depth: int) -> pd.DataFrame:
    ordered = all_rows.sort_values(["run_id", "window_index"], kind="stable").reset_index(drop=True)
    key = (profile, 0 if profile.endswith("control") else depth)
    return feature_sets[key].loc[~ordered["warmup"].astype(bool)].reset_index(drop=True)


def make_gate(name: str):
    if name == "logistic_regression":
        return Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
            ("model", LogisticRegression(C=1.0, class_weight="balanced", max_iter=2000, random_state=42)),
        ])
    if name == "random_forest":
        model = RandomForestClassifier(n_estimators=300, max_depth=6, min_samples_leaf=2,
                                       class_weight="balanced_subsample", random_state=42, n_jobs=-1)
    elif name == "hist_gradient_boosting":
        model = HistGradientBoostingClassifier(learning_rate=0.05, max_iter=200, max_leaf_nodes=15,
                                               l2_regularization=1.0, random_state=42)
    else:
        raise KeyError(name)
    return Pipeline([("imputer", SimpleImputer(strategy="median")), ("model", model)])


def make_subtype(name: str):
    if name == "random_forest":
        model = RandomForestClassifier(n_estimators=300, max_depth=6, min_samples_leaf=2,
                                       class_weight="balanced_subsample", random_state=42, n_jobs=-1)
    elif name == "hist_gradient_boosting":
        model = HistGradientBoostingClassifier(learning_rate=0.05, max_iter=200, max_leaf_nodes=15,
                                               l2_regularization=1.0, random_state=42)
    else:
        raise KeyError(name)
    return Pipeline([("imputer", SimpleImputer(strategy="median")), ("model", model)])


def positive_probability(model, X) -> np.ndarray:
    probabilities = model.predict_proba(X)
    return probabilities[:, list(model.classes_).index(1)]


def aligned_probabilities(model, X, classes: list[str] = ATTACK_CLASSES) -> np.ndarray:
    raw = model.predict_proba(X)
    aligned = np.zeros((len(X), len(classes)), dtype=float)
    for source, name in enumerate(model.classes_):
        aligned[:, classes.index(str(name))] = raw[:, source]
    return aligned


def calibrate_aligned(calibrator: GroupAwareSigmoidCalibrator, probabilities: np.ndarray,
                      classes: list[str] = ATTACK_CLASSES) -> np.ndarray:
    raw = calibrator.predict_proba(probabilities)
    aligned = np.zeros((len(probabilities), len(classes)), dtype=float)
    for source, name in enumerate(calibrator.model.classes_):
        aligned[:, classes.index(str(name))] = raw[:, source]
    return aligned


def expected_calibration_error(y_true: np.ndarray, probabilities: np.ndarray, bins: int = 10) -> float:
    y_true = np.asarray(y_true)
    probabilities = np.asarray(probabilities, float)
    if probabilities.ndim == 1:
        confidence = probabilities
        correct = y_true.astype(int)
    else:
        predictions = np.argmax(probabilities, axis=1)
        confidence = np.max(probabilities, axis=1)
        correct = (predictions == y_true.astype(int)).astype(int)
    result = 0.0
    for lower, upper in zip(np.linspace(0, 1, bins + 1)[:-1], np.linspace(0, 1, bins + 1)[1:]):
        selected = (confidence > lower) & (confidence <= upper)
        if selected.any():
            result += selected.mean() * abs(correct[selected].mean() - confidence[selected].mean())
    return float(result)


@dataclass(frozen=True)
class DecisionParameters:
    gate_benign_threshold: float
    gate_attack_threshold: float
    subtype_confidence_threshold: float
    ood_threshold: float
    temporal_variant: str
    temporal_alpha: float = 0.7
    temporal_activation_threshold: float = 0.65


def decide_rows(rows: pd.DataFrame, gate_probability: np.ndarray, subtype_probability: np.ndarray,
                ood_score: np.ndarray, parameters: DecisionParameters) -> pd.DataFrame:
    """Применяет frozen policy причинно, в исходном порядке каждого run."""
    output = []
    accumulators: dict[str, TemporalEvidenceAccumulator] = {}
    for position, (_, row) in enumerate(rows.iterrows()):
        run_id = str(row["run_id"])
        accumulator = accumulators.setdefault(
            run_id,
            TemporalEvidenceAccumulator(parameters.temporal_variant, parameters.temporal_alpha,
                                        parameters.temporal_activation_threshold),
        )
        probability = float(gate_probability[position])
        temporal = bool(accumulator.update(probability, run_id))
        ood = bool(ood_score[position] > parameters.ood_threshold)
        subtype_position = int(np.argmax(subtype_probability[position]))
        subtype = ATTACK_CLASSES[subtype_position]
        subtype_confidence = float(subtype_probability[position, subtype_position])
        if ood and not temporal:
            state = "insufficient_evidence"
        elif probability <= parameters.gate_benign_threshold:
            state = "benign"
        elif probability < parameters.gate_attack_threshold and not temporal:
            state = "insufficient_evidence"
        elif subtype_confidence < parameters.subtype_confidence_threshold:
            state = "suspicious_unclassified"
        else:
            state = f"attack_candidate:{subtype}"
        output.append({
            "decision_state": state,
            "gate_probability": probability,
            "ood_score": float(ood_score[position]),
            "is_ood": ood,
            "temporal_evidence": temporal,
            "subtype_prediction": subtype,
            "subtype_confidence": subtype_confidence,
        })
    return pd.DataFrame(output)


def _closed_prediction(state: str) -> str:
    if state.startswith("attack_candidate:"):
        return state.split(":", 1)[1]
    if state == "benign":
        return "benign"
    return "unresolved"


def window_metrics(rows: pd.DataFrame, decisions: pd.DataFrame) -> dict:
    labels = rows["label"].astype(str).to_numpy()
    states = decisions["decision_state"].astype(str).to_numpy()
    benign = labels == "benign"
    attack = ~benign
    alerts = np.array([state.startswith("attack_candidate:") or state == "suspicious_unclassified" for state in states])
    high = np.array([state.startswith("attack_candidate:") for state in states])
    unresolved = np.isin(states, ["insufficient_evidence", "suspicious_unclassified"])
    covered = ~unresolved
    if "gate_probability" in decisions and "subtype_prediction" in decisions:
        closed_for_score = np.where(decisions["gate_probability"].to_numpy() < .5, "benign",
                                    decisions["subtype_prediction"].astype(str).to_numpy())
    else:
        closed_for_score = np.array([_closed_prediction(state) for state in states])
        closed_for_score = np.where(closed_for_score == "unresolved", "benign", closed_for_score)
    closed = np.array([_closed_prediction(state) for state in states])
    operational_class = np.array([state.split(":", 1)[1] if state.startswith("attack_candidate:") else state for state in states])
    operational_true = np.where(benign, "benign", "attack")
    operational_pred = np.where(states == "benign", "benign", np.where(alerts, "attack", "unresolved"))
    hard = benign & rows["hard_negative_target_class"].fillna("").astype(str).ne("").to_numpy()
    subtype_true = labels[attack]
    subtype_pred = np.array([value if value in ATTACK_CLASSES else "unresolved" for value in closed[attack]])
    per_class = {}
    labels_all = ["benign"] + ATTACK_CLASSES
    precision, recall, f1, support = precision_recall_fscore_support(labels, closed_for_score, labels=labels_all, zero_division=0)
    for index, name in enumerate(labels_all):
        per_class[name] = {"precision": float(precision[index]), "recall": float(recall[index]),
                           "f1": float(f1[index]), "support": int(support[index])}
    result = {
        "support": int(len(rows)),
        "accuracy": float(accuracy_score(labels, operational_class)),
        "balanced_accuracy": float(balanced_accuracy_score(labels, operational_class)),
        "operational_macro_f1": float(f1_score(operational_true, operational_pred, labels=["benign", "attack", "unresolved"], average="macro", zero_division=0)),
        "weighted_f1": float(f1_score(labels, operational_class, average="weighted", zero_division=0)),
        "closed_set_accuracy": float(accuracy_score(labels, closed_for_score)),
        "closed_set_balanced_accuracy": float(balanced_accuracy_score(labels, closed_for_score)),
        "closed_set_macro_f1": float(f1_score(labels, closed_for_score, labels=labels_all, average="macro", zero_division=0)),
        "closed_set_benign_recall": float(np.mean(closed_for_score[benign] == "benign")) if benign.any() else 0.0,
        "closed_set_FPR": float(np.mean(closed_for_score[benign] != "benign")) if benign.any() else 0.0,
        "closed_set_attack_macro_recall": float(np.mean([np.mean(closed_for_score[labels == name] == name) for name in ATTACK_CLASSES if np.any(labels == name)])) if attack.any() else 0.0,
        "benign_recall": float(np.mean(states[benign] == "benign")) if benign.any() else 0.0,
        "false_positive_count": int(np.sum(benign & (states != "benign"))),
        "false_positive_rate": float(np.mean(states[benign] != "benign")) if benign.any() else 0.0,
        "high_severity_false_positive_count": int(np.sum(benign & high)),
        "high_severity_false_positive_rate": float(np.mean(high[benign])) if benign.any() else 0.0,
        "hard_negative_benign_recall": float(np.mean(states[hard] == "benign")) if hard.any() else 0.0,
        "hard_negative_false_positive_rate": float(np.mean(states[hard] != "benign")) if hard.any() else 0.0,
        "attack_alert_recall": float(np.mean(alerts[attack])) if attack.any() else 0.0,
        "attack_to_benign_false_negative_count": int(np.sum(attack & (states == "benign"))),
        "attack_to_benign_false_negative_rate": float(np.mean(states[attack] == "benign")) if attack.any() else 0.0,
        "attack_unresolved_count": int(np.sum(attack & unresolved)),
        "attack_unresolved_rate": float(np.mean(unresolved[attack])) if attack.any() else 0.0,
        "attack_subtype_macro_recall": float(precision_recall_fscore_support(subtype_true, subtype_pred, labels=ATTACK_CLASSES, average="macro", zero_division=0)[1]) if attack.any() else 0.0,
        "decision_coverage": float(np.mean(covered)),
        "insufficient_evidence_count": int(np.sum(states == "insufficient_evidence")),
        "insufficient_evidence_rate": float(np.mean(states == "insufficient_evidence")),
        "benign_insufficient_evidence_rate": float(np.mean(states[benign] == "insufficient_evidence")) if benign.any() else 0.0,
        "suspicious_unclassified_count": int(np.sum(states == "suspicious_unclassified")),
        "suspicious_unclassified_rate": float(np.mean(states == "suspicious_unclassified")),
        "zero_recall_attack_classes": [name for name in ATTACK_CLASSES if per_class[name]["recall"] == 0.0],
        "per_class": per_class,
        "confusion_matrix": {"labels": labels_all, "values": confusion_matrix(labels, closed_for_score, labels=labels_all).tolist()},
    }
    benign_scores = precision_recall_fscore_support(labels == "benign", states == "benign", average="binary", zero_division=0)
    result["benign_precision"] = float(benign_scores[0])
    result["benign_f1"] = float(benign_scores[2])
    operational_scores = precision_recall_fscore_support(operational_true, operational_pred, labels=["benign", "attack", "unresolved"], average="macro", zero_division=0)
    result["operational_macro_precision"] = float(operational_scores[0])
    result["operational_macro_recall"] = float(operational_scores[1])
    if attack.any():
        subtype_scores = precision_recall_fscore_support(subtype_true, subtype_pred, labels=ATTACK_CLASSES, average="macro", zero_division=0)
        result["attack_subtype_macro_precision"] = float(subtype_scores[0])
        result["attack_subtype_macro_f1"] = float(subtype_scores[2])
    else:
        result["attack_subtype_macro_precision"] = 0.0
        result["attack_subtype_macro_f1"] = 0.0
    return result


def episode_metrics(rows: pd.DataFrame, decisions: pd.DataFrame) -> dict:
    extra = decisions[[column for column in decisions.columns if column not in rows.columns]]
    combined = pd.concat([rows.reset_index(drop=True), extra.reset_index(drop=True)], axis=1)
    episodes = []
    for (run_id, episode_id), part in combined.groupby(["run_id", "episode_id"], sort=False):
        label = str(part["label"].iloc[0])
        states = part["decision_state"].astype(str).tolist()
        alerts = [state != "benign" and state != "insufficient_evidence" for state in states]
        high = [state.startswith("attack_candidate:") for state in states]
        first = next((index + 1 for index, value in enumerate(alerts) if value), None)
        episodes.append({"run_id": run_id, "episode_id": episode_id, "label": label,
                         "alert": any(alerts), "high_alert": any(high),
                         "unresolved": not any(alerts), "time_to_alert": first})
    frame = pd.DataFrame(episodes)
    benign = frame["label"] == "benign"
    attack = ~benign
    times = frame.loc[attack & frame["alert"], "time_to_alert"].dropna().astype(float)
    per_class = {}
    for name in ATTACK_CLASSES:
        selected = frame["label"] == name
        per_class[name] = {
            "support": int(selected.sum()),
            "episode_recall": float(frame.loc[selected, "alert"].mean()) if selected.any() else 0.0,
            "median_time_to_alert": float(frame.loc[selected & frame["alert"], "time_to_alert"].median()) if (selected & frame["alert"]).any() else None,
        }
    return {
        "benign_episode_support": int(benign.sum()), "attack_episode_support": int(attack.sum()),
        "benign_episode_false_alert_count": int(frame.loc[benign, "alert"].sum()),
        "benign_episode_false_alert_rate": float(frame.loc[benign, "alert"].mean()),
        "attack_episode_detected_count": int(frame.loc[attack, "alert"].sum()),
        "attack_episode_recall": float(frame.loc[attack, "alert"].mean()),
        "attack_episode_unresolved_count": int(frame.loc[attack, "unresolved"].sum()),
        "attack_episode_unresolved_rate": float(frame.loc[attack, "unresolved"].mean()),
        "attack_episode_to_benign_miss_count": int(frame.loc[attack, "unresolved"].sum()),
        "attack_episode_to_benign_miss_rate": float(frame.loc[attack, "unresolved"].mean()),
        "time_to_first_alert_mean": float(times.mean()) if len(times) else None,
        "time_to_first_alert_median": float(times.median()) if len(times) else None,
        "time_to_first_alert_max": float(times.max()) if len(times) else None,
        "zero_recall_attack_episode_classes": [name for name, value in per_class.items() if value["episode_recall"] == 0.0],
        "per_attack_class": per_class,
        "episodes": episodes,
    }


def candidate_passes(metrics: dict, episodes: dict) -> tuple[bool, dict]:
    checks = {
        "minimum_attack_alert_recall": metrics["attack_alert_recall"] >= 0.90,
        "maximum_attack_to_benign_false_negative_rate": metrics["attack_to_benign_false_negative_rate"] <= 0.05,
        "minimum_benign_recall": metrics["benign_recall"] >= 0.82,
        "maximum_false_positive_rate": metrics["false_positive_rate"] <= 0.15,
        "maximum_high_severity_false_positive_rate": metrics["high_severity_false_positive_rate"] <= 0.10,
        "minimum_hard_negative_benign_recall": metrics["hard_negative_benign_recall"] >= 0.75,
        "minimum_decision_coverage": metrics["decision_coverage"] >= 0.75,
        "maximum_attack_unresolved_rate": metrics["attack_unresolved_rate"] <= 0.10,
        "maximum_benign_insufficient_evidence_rate": metrics["benign_insufficient_evidence_rate"] <= 0.20,
        "minimum_attack_subtype_macro_recall": metrics["attack_subtype_macro_recall"] >= 0.80,
        "no_zero_recall_attack_classes": len(metrics["zero_recall_attack_classes"]) == 0,
        "minimum_attack_episode_recall": episodes["attack_episode_recall"] >= 0.95,
        "maximum_benign_episode_false_alert_rate": episodes["benign_episode_false_alert_rate"] <= 0.20,
        "maximum_attack_episode_unresolved_rate": episodes["attack_episode_unresolved_rate"] <= 0.05,
        "maximum_median_time_to_alert_windows": episodes["time_to_first_alert_median"] is not None and episodes["time_to_first_alert_median"] <= 2,
        "no_zero_recall_attack_episode_class": len(episodes["zero_recall_attack_episode_classes"]) == 0,
    }
    return all(checks.values()), checks


def parameter_grid(ood_scores: np.ndarray) -> list[DecisionParameters]:
    values = []
    quantiles = [float(np.quantile(ood_scores, q)) for q in (0.95, 0.975, 0.99)]
    variants = [("none", .7, .65), ("2_of_3", .7, .65), ("2_of_4", .7, .65)]
    variants += [("decayed", alpha, activation) for alpha in (.5, .7) for activation in (.55, .65, .75)]
    for benign_threshold in (.20, .30, .40):
        for attack_threshold in (.60, .70, .80):
            for subtype_threshold in (.35, .45, .55, .65):
                for ood_threshold in quantiles:
                    for variant, alpha, activation in variants:
                        values.append(DecisionParameters(benign_threshold, attack_threshold, subtype_threshold,
                                                         ood_threshold, variant, alpha, activation))
    return values


def select_parameters(rows: pd.DataFrame, gate_probability: np.ndarray, subtype_probability: np.ndarray,
                      ood_scores: np.ndarray) -> tuple[DecisionParameters, dict]:
    labels = rows["label"].astype(str).to_numpy()
    benign = labels == "benign"
    attack = ~benign
    hard = benign & rows["hard_negative_target_class"].fillna("").astype(str).ne("").to_numpy()
    subtype_index = np.argmax(subtype_probability, axis=1)
    subtype_confidence = np.max(subtype_probability, axis=1)
    subtype_truth = np.array([ATTACK_CLASSES.index(value) if value in ATTACK_CLASSES else -1 for value in labels])
    episode_groups = [part.to_numpy() for _, part in rows.reset_index().groupby(["run_id", "episode_id"], sort=False)["index"]]
    temporal_cache = {}
    for variant, alpha, activation in sorted({(p.temporal_variant, p.temporal_alpha, p.temporal_activation_threshold)
                                               for p in parameter_grid(ood_scores[benign])}):
        accumulator_by_run = {}
        values = np.zeros(len(rows), dtype=bool)
        for position, run_id in enumerate(rows["run_id"].astype(str)):
            accumulator = accumulator_by_run.setdefault(run_id, TemporalEvidenceAccumulator(variant, alpha, activation))
            values[position] = accumulator.update(gate_probability[position], run_id)
        temporal_cache[(variant, alpha, activation)] = values
    best_rank = None
    best_parameters = None
    for parameters in parameter_grid(ood_scores[benign]):
        temporal = temporal_cache[(parameters.temporal_variant, parameters.temporal_alpha,
                                   parameters.temporal_activation_threshold)]
        ood = ood_scores > parameters.ood_threshold
        # codes: 0 benign, 1 insufficient, 2 suspicious_unclassified, 3+ attack subtype.
        codes = np.ones(len(rows), dtype=np.int8)
        codes[(~ood | temporal) & (gate_probability <= parameters.gate_benign_threshold)] = 0
        attack_path = (~ood | temporal) & ((gate_probability >= parameters.gate_attack_threshold) | temporal)
        codes[attack_path & (subtype_confidence < parameters.subtype_confidence_threshold)] = 2
        codes[attack_path & (subtype_confidence >= parameters.subtype_confidence_threshold)] = 3 + subtype_index[attack_path & (subtype_confidence >= parameters.subtype_confidence_threshold)]
        alert = codes >= 2
        high = codes >= 3
        unresolved = (codes == 1) | (codes == 2)
        benign_recall = float(np.mean(codes[benign] == 0))
        fpr = 1.0 - benign_recall
        high_fpr = float(np.mean(high[benign]))
        hard_recall = float(np.mean(codes[hard] == 0)) if hard.any() else 0.0
        attack_alert = float(np.mean(alert[attack]))
        attack_to_benign = float(np.mean(codes[attack] == 0))
        attack_unresolved = float(np.mean(unresolved[attack]))
        coverage = float(np.mean(~unresolved))
        benign_insufficient = float(np.mean(codes[benign] == 1))
        recalls = [float(np.mean(codes[(subtype_truth == index)] == 3 + index)) for index in range(len(ATTACK_CLASSES))]
        subtype_macro = float(np.mean(recalls))
        window_pass = (attack_alert >= .90 and attack_to_benign <= .05 and benign_recall >= .82 and
                       fpr <= .15 and high_fpr <= .10 and hard_recall >= .75 and coverage >= .75 and
                       attack_unresolved <= .10 and benign_insufficient <= .20 and subtype_macro >= .80 and
                       min(recalls) > 0)
        episode_pass = False
        if window_pass:
            benign_false = []
            attack_detected = []
            times = []
            class_detected = {name: [] for name in ATTACK_CLASSES}
            for indices in episode_groups:
                is_attack = labels[indices[0]] != "benign"
                detected = bool(np.any(alert[indices]))
                if is_attack:
                    attack_detected.append(detected)
                    class_detected[labels[indices[0]]].append(detected)
                    if detected:
                        times.append(int(np.argmax(alert[indices])) + 1)
                else:
                    benign_false.append(detected)
            episode_pass = (np.mean(attack_detected) >= .95 and np.mean(benign_false) <= .20 and
                            (1 - np.mean(attack_detected)) <= .05 and times and np.median(times) <= 2 and
                            all(values and np.mean(values) > 0 for values in class_detected.values()))
        rank = (int(window_pass and episode_pass), -fpr, benign_recall, attack_alert,
                (benign_recall + attack_alert + subtype_macro) / 3, coverage, -attack_unresolved)
        if best_rank is None or rank > best_rank:
            best_rank = rank
            best_parameters = parameters
    assert best_parameters is not None
    decisions = decide_rows(rows, gate_probability, subtype_probability, ood_scores, best_parameters)
    metrics = window_metrics(rows, decisions)
    episodes = episode_metrics(rows, decisions)
    passed, checks = candidate_passes(metrics, episodes)
    return best_parameters, {"metrics": metrics, "episode_metrics": episodes,
                             "policy_passed": passed, "policy_checks": checks}


def model_parameters(name: str, task: str) -> dict:
    if name == "logistic_regression":
        return {"C": 1.0, "class_weight": "balanced", "max_iter": 2000, "random_state": 42}
    if name == "random_forest":
        return {"n_estimators": 300, "max_depth": 6, "min_samples_leaf": 2,
                "class_weight": "balanced_subsample", "random_state": 42, "n_jobs": -1}
    return {"learning_rate": 0.05, "max_iter": 200, "max_leaf_nodes": 15,
            "l2_regularization": 1.0, "random_state": 42}


def estimator_feature_importance(model, feature_names: list[str]) -> list[dict]:
    estimator = model.named_steps["model"]
    if hasattr(estimator, "feature_importances_"):
        values = estimator.feature_importances_
    elif hasattr(estimator, "coef_"):
        values = np.mean(np.abs(estimator.coef_), axis=0)
    else:
        return []
    return [{"feature": name, "importance": float(value)} for name, value in
            sorted(zip(feature_names, values), key=lambda pair: -pair[1])]
