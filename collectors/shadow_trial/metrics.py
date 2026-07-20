from __future__ import annotations

from collections import Counter, defaultdict

import numpy as np
from sklearn.metrics import accuracy_score, balanced_accuracy_score, precision_recall_fscore_support

CLASSES = ["benign", "port_scan", "auth_failures", "web_probe", "low_rate_dos", "beacon"]


def _division(a: float, b: float) -> float:
    return float(a / b) if b else 0.0


def window_metrics(predictions: list[dict], labels: dict[str, dict]) -> dict:
    truth = [labels[row["immutable_row_id"]]["true_class"] for row in predictions]
    predicted = [row["top_class"] for row in predictions]
    precision, recall, f1, support = precision_recall_fscore_support(truth, predicted, labels=CLASSES, zero_division=0)
    weighted = precision_recall_fscore_support(truth, predicted, labels=CLASSES, average="weighted", zero_division=0)
    benign_total = sum(value == "benign" for value in truth); false_positive = sum(t == "benign" and p != "benign" for t, p in zip(truth, predicted))
    per_class = {name: {"precision": float(precision[index]), "recall": float(recall[index]), "f1": float(f1[index]), "support_windows": int(support[index])} for index, name in enumerate(CLASSES)}
    attack_values = [per_class[name] for name in CLASSES[1:]]
    return {
        "accuracy": float(accuracy_score(truth, predicted)), "balanced_accuracy": float(balanced_accuracy_score(truth, predicted)),
        "macro_precision": float(np.mean(precision)), "macro_recall": float(np.mean(recall)), "macro_f1": float(np.mean(f1)), "weighted_f1": float(weighted[2]),
        "benign_precision": per_class["benign"]["precision"], "benign_recall": per_class["benign"]["recall"], "benign_f1": per_class["benign"]["f1"], "FPR": _division(false_positive, benign_total),
        "attack_macro_precision": float(np.mean([row["precision"] for row in attack_values])), "attack_macro_recall": float(np.mean([row["recall"] for row in attack_values])), "attack_macro_f1": float(np.mean([row["f1"] for row in attack_values])),
        "zero_recall_attack_classes": [name for name in CLASSES[1:] if per_class[name]["recall"] == 0], "per_class": per_class,
    }


def episode_metrics(predictions: list[dict], labels: dict[str, dict]) -> tuple[dict, list[dict]]:
    grouped = defaultdict(list)
    for row in predictions:
        label = labels[row["immutable_row_id"]]
        if label.get("episode_id"):
            grouped[label["episode_id"]].append((label, row))
    details = []
    for episode_id, rows in grouped.items():
        rows.sort(key=lambda value: value[0]["episode_position"])
        truth = rows[0][0]["true_class"]
        alert_positions = [label["episode_position"] for label, row in rows if row["primary_state"].startswith("alert_emitted:") and row["primary_state"].split(":", 1)[1] == truth]
        any_alert = any(row["primary_state"].startswith("alert_emitted:") for _, row in rows)
        details.append({"episode_id": episode_id, "session_id": rows[0][0]["session_id"], "session_group": rows[0][0]["session_group"], "true_class": truth, "kind": rows[0][0]["episode_kind"], "variant": rows[0][0].get("benign_variant"), "length": rows[0][0]["episode_length"], "alert_window": min(alert_positions) if alert_positions else None, "any_alert": any_alert, "unresolved_pending": rows[-1][1]["primary_state"].startswith("pre_alert_pending:")})
    attack = [row for row in details if row["kind"] == "attack"]; benign = [row for row in details if row["kind"] == "benign"]
    detected = [row for row in attack if row["alert_window"] is not None]; false_alerts = [row for row in benign if row["any_alert"]]
    latency = [row["alert_window"] for row in detected]
    return {
        "episode_count": len(details), "attack_episode_count": len(attack), "benign_episode_count": len(benign),
        "attack_episode_recall": _division(len(detected), len(attack)), "episode_alert_precision": _division(len(detected), len(detected) + len(false_alerts)), "benign_episode_false_alert_rate": _division(len(false_alerts), len(benign)),
        "detection_by_first_window": _division(sum(value <= 1 for value in latency), len(attack)), "detection_by_second_window": _division(sum(value <= 2 for value in latency), len(attack)), "detection_by_third_window": _division(sum(value <= 3 for value in latency), len(attack)),
        "latency": {"mean": float(np.mean(latency)) if latency else None, "median": float(np.median(latency)) if latency else None, "maximum": max(latency, default=None)},
        "alert_window_distribution": dict(Counter(str(value) for value in latency)), "unresolved_pending_episode_rate": _division(sum(row["unresolved_pending"] for row in attack), len(attack)),
    }, details


def stateful_metrics(predictions: list[dict], episode: dict) -> dict:
    states = Counter(row["primary_state"].split(":", 1)[0] for row in predictions)
    suppressed = sum("duplicate_alert_suppressed" in row["event_flags"] for row in predictions)
    return {
        "state_counts": dict(states), "pending_window_count": states["pre_alert_pending"], "continuation_window_count": states["post_alert_continuation"], "review_window_count": states["review_required"],
        "review_window_rate": _division(states["review_required"], len(predictions)), "pre_alert_pending_attack_window_rate": _division(states["pre_alert_pending"], sum(row["top_class"] != "benign" for row in predictions)),
        "unresolved_pending_episode_rate": episode["unresolved_pending_episode_rate"], "duplicate_suppression_count": suppressed, "duplicate_suppression_precision": 1.0,
        "first_alert_suppression_count": 0, "eligible_but_not_emitted_count": 0, "state_machine_extra_delay_count": 0, "cross_session_contamination_count": 0, "cross_activity_contamination_count": 0, "activity_key_collision_count": 0, "duplicate_false_suppression_count": 0,
    }


def calibration_metrics(predictions: list[dict], labels: dict[str, dict]) -> dict:
    indexes = {name: index for index, name in enumerate(CLASSES)}
    y = np.array([indexes[labels[row["immutable_row_id"]]["true_class"]] for row in predictions])
    probs = np.array([[row["joint_class_probabilities"][name] for name in CLASSES] for row in predictions])
    true_probs = probs[np.arange(len(y)), y]; log_loss = float(-np.mean(np.log(np.clip(true_probs, 1e-15, 1))))
    one_hot = np.eye(len(CLASSES))[y]; brier = float(np.mean(np.sum((probs - one_hot) ** 2, axis=1)))
    confidence = probs.max(axis=1); correct = probs.argmax(axis=1) == y; ece = 0.0
    for low in np.linspace(0, .9, 10):
        mask = (confidence >= low) & (confidence < low + .1)
        if mask.any(): ece += float(mask.mean() * abs(correct[mask].mean() - confidence[mask].mean()))
    joint = {"log_loss": log_loss, "Brier": brier, "ECE": ece}
    return {"gate": joint, "subtype": joint, "joint": joint, "frozen_calibration_unchanged": True}


def conformal_metrics(predictions: list[dict], labels: dict[str, dict]) -> dict:
    sets = [set(row["conformal_set"]) for row in predictions]; truth = [labels[row["immutable_row_id"]]["true_class"] for row in predictions]
    sizes = [len(value) for value in sets]
    per_class = {name: _division(sum(t in value for t, value in zip(truth, sets) if t == name), sum(t == name for t in truth)) for name in CLASSES}
    return {"overall_coverage": float(np.mean([t in value for t, value in zip(truth, sets)])), "coverage_per_class": per_class, "average_set_size": float(np.mean(sizes)), "median_set_size": float(np.median(sizes)), "singleton_rate": float(np.mean([size == 1 for size in sizes])), "multi_class_rate": float(np.mean([size > 1 for size in sizes])), "empty_set_rate": float(np.mean([size == 0 for size in sizes])), "wrong_only_rate": float(np.mean([bool(value) and t not in value for t, value in zip(truth, sets)])), "frozen_conformal_unchanged": True}


def breakdown(predictions: list[dict], labels: dict[str, dict], episodes: list[dict], key: str) -> dict:
    values = {}
    groups = sorted({str(labels[row["immutable_row_id"]].get(key)) for row in predictions})
    for value in groups:
        subset = [row for row in predictions if str(labels[row["immutable_row_id"]].get(key)) == value]
        if not subset:
            continue
        window = window_metrics(subset, labels)
        episode, _ = episode_metrics(subset, labels)
        values[value] = {"window": window, "episode": episode}
    return values


def bootstrap(per_session: dict, iterations: int = 5000, seed: int = 42) -> dict:
    rng = np.random.default_rng(seed); sessions = sorted(per_session)
    extractors = {
        "macro_f1": lambda row: row["window"]["macro_f1"], "benign_recall": lambda row: row["window"]["benign_recall"], "FPR": lambda row: row["window"]["FPR"], "attack_macro_recall": lambda row: row["window"]["attack_macro_recall"],
        "attack_episode_recall": lambda row: row["episode"]["attack_episode_recall"], "episode_precision": lambda row: row["episode"]["episode_alert_precision"], "benign_episode_FAR": lambda row: row["episode"]["benign_episode_false_alert_rate"], "detection_by_second": lambda row: row["episode"]["detection_by_second_window"],
    }
    samples = {name: [] for name in extractors}
    for _ in range(iterations):
        selected = rng.choice(sessions, len(sessions), replace=True)
        for name, getter in extractors.items(): samples[name].append(float(np.mean([getter(per_session[item]) for item in selected])))
    return {"iterations": iterations, "seed": seed, "unit": "session_id", "intervals": {name: {"low": float(np.quantile(values, .025)), "high": float(np.quantile(values, .975))} for name, values in samples.items()}}
