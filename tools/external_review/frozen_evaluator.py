"""Детерминированный frozen evaluator v1 для blind episode predictions."""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any


VERSION = "frozen_external_evaluator_v1"
CLASSES = ("benign", "auth_failures", "beacon", "low_rate_dos", "port_scan", "web_probe")


class EvaluationError(ValueError):
    pass


def _unique(rows: list[dict[str, Any]], name: str) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        episode_id = row.get("episode_id")
        if not isinstance(episode_id, str) or not episode_id:
            raise EvaluationError(f"invalid_episode_id:{name}")
        if episode_id in result:
            raise EvaluationError(f"duplicate_episode_id:{name}:{episode_id}")
        result[episode_id] = row
    return result


def _safe_div(numerator: int, denominator: int) -> float:
    return numerator / denominator if denominator else 0.0


def _wilson(success: int, total: int, z: float = 1.959963984540054) -> list[float]:
    if total == 0:
        return [0.0, 0.0]
    p = success / total
    denominator = 1 + z * z / total
    center = (p + z * z / (2 * total)) / denominator
    half = z * math.sqrt((p * (1 - p) + z * z / (4 * total)) / total) / denominator
    return [max(0.0, center - half), min(1.0, center + half)]


def evaluate(predictions: list[dict[str, Any]], labels: list[dict[str, Any]]) -> dict[str, Any]:
    pred = _unique(predictions, "predictions")
    truth = _unique(labels, "labels")
    unknown_pred = sorted(set(pred) - set(truth))
    missing = sorted(set(truth) - set(pred))
    if unknown_pred:
        raise EvaluationError("prediction_unknown_episode")
    if missing:
        raise EvaluationError("missing_prediction")
    for row in truth.values():
        if row.get("class") not in CLASSES:
            raise EvaluationError("unsupported_label_class")
    matrix = {actual: {guess: 0 for guess in CLASSES} for actual in CLASSES}
    abstentions = 0
    correct = 0
    covered = 0
    false_positive_benign = 0
    false_negative_attack = 0
    for episode_id in sorted(truth):
        actual = truth[episode_id]["class"]
        row = pred[episode_id]
        abstained = row.get("abstained")
        guess = row.get("predicted_class")
        if not isinstance(abstained, bool) or abstained != (guess is None):
            raise EvaluationError("invalid_abstention")
        if abstained:
            abstentions += 1
            continue
        if guess not in CLASSES:
            raise EvaluationError("unsupported_prediction_class")
        covered += 1
        matrix[actual][guess] += 1
        correct += int(actual == guess)
        false_positive_benign += int(actual == "benign" and guess != "benign")
        false_negative_attack += int(actual != "benign" and guess == "benign")
    per_class: dict[str, dict[str, float | int]] = {}
    f1_values: list[float] = []
    recalls: list[float] = []
    weighted_f1_sum = 0.0
    for class_name in CLASSES:
        tp = matrix[class_name][class_name]
        fp = sum(matrix[other][class_name] for other in CLASSES if other != class_name)
        fn = sum(matrix[class_name][other] for other in CLASSES if other != class_name)
        support = sum(1 for row in truth.values() if row["class"] == class_name)
        precision = _safe_div(tp, tp + fp)
        recall = _safe_div(tp, tp + fn)
        f1 = _safe_div(2 * tp, 2 * tp + fp + fn)
        per_class[class_name] = {
            "precision": precision, "recall": recall, "f1": f1, "support": support,
        }
        f1_values.append(f1)
        recalls.append(recall)
        weighted_f1_sum += f1 * support
    total = len(truth)
    return {
        "evaluator_version": VERSION,
        "class_taxonomy": list(CLASSES),
        "dataset_composition": {"episode_count": total, "per_class": {name: per_class[name]["support"] for name in CLASSES}},
        "confusion_matrix": matrix,
        "per_class": per_class,
        "macro_f1": sum(f1_values) / len(CLASSES),
        "weighted_f1": weighted_f1_sum / total,
        "balanced_accuracy": sum(recalls) / len(CLASSES),
        "false_positive_benign_as_attack_count": false_positive_benign,
        "false_negative_attack_as_benign_count": false_negative_attack,
        "abstention_count": abstentions,
        "abstention_rate": abstentions / total,
        "coverage": covered / total,
        "selective_accuracy": _safe_div(correct, covered),
        "selective_accuracy_interval_95": _wilson(correct, covered),
        "coverage_interval_95": _wilson(covered, total),
        "missing_prediction_count": 0,
        "duplicate_prediction_count": 0,
        "invalid_prediction_count": 0,
        "aggregation_level": "episode",
        "protocol_rehearsal_only": True,
        "scientific_evidence": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("predictions", type=Path)
    parser.add_argument("labels", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    predictions = json.loads(args.predictions.read_text(encoding="utf-8"))
    labels = json.loads(args.labels.read_text(encoding="utf-8"))
    result = evaluate(predictions, labels)
    args.output.write_text(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
