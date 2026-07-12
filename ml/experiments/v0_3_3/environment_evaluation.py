"""Frozen-model external evaluation primitives for v0.3.3.

This module intentionally has no fitting operation.  The supplied estimator is
only transformed and predicted against externally produced sensor windows.
"""
from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml
from sklearn.metrics import accuracy_score, balanced_accuracy_score, f1_score, precision_recall_fscore_support, precision_score, recall_score


ATTACK_LABELS = ("port_scan", "auth_failures", "web_probe", "low_rate_dos", "beacon_simulation")
LEAKAGE_COLUMNS = {
    "run_id", "label", "label_type", "scenario_id", "execution_id", "scenario_execution_key",
    "campaign_id", "campaign_version", "campaign_role", "campaign_seed", "environment_group",
    "topology_variant_id", "background_variant_id", "temporal_variant_id", "robustness_parameter_hash",
    "marker_start_uid", "marker_end_uid", "zeek_uid", "raw_uri", "raw_hostname",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_policy(path: Path) -> tuple[dict[str, Any], str]:
    raw = path.read_bytes()
    data = yaml.safe_load(raw) or {}
    policy = data.get("evaluation_policy")
    if not isinstance(policy, dict):
        raise ValueError("В policy отсутствует evaluation_policy.")
    return policy, hashlib.sha256(raw).hexdigest()


def validate_feature_frame(frame: pd.DataFrame, ordered_features: list[str]) -> pd.DataFrame:
    leakage = sorted(set(frame.columns) & LEAKAGE_COLUMNS)
    if leakage:
        raise ValueError("Metadata leakage в наборе признаков: " + ", ".join(leakage))
    missing = sorted(set(ordered_features) - set(frame.columns))
    unexpected = sorted(set(frame.columns) - set(ordered_features))
    if missing or unexpected:
        raise ValueError(f"Набор признаков не совпадает с frozen model; missing={missing}, unexpected={unexpected}")
    return frame.loc[:, ordered_features]


def load_environment_datasets(paths: list[Path], ordered_features: list[str]) -> tuple[pd.DataFrame, dict[str, str]]:
    frames: list[pd.DataFrame] = []
    hashes: dict[str, str] = {}
    seen_executions: set[str] = set()
    for path in paths:
        frame = pd.read_csv(path)
        required = {"run_id", "execution_id", "label", "feature_profile", "observation_source", "sensor_type", "execution_mode", "synthetic"}
        missing = required - set(frame.columns)
        if missing:
            raise ValueError(f"{path}: отсутствуют поля {sorted(missing)}")
        synthetic = frame["synthetic"].astype(str).str.strip().str.lower().eq("true")
        if not (frame["feature_profile"] == "network_sensor_v0_3").all() or not (frame["observation_source"] == "network_sensor").all() or not (frame["sensor_type"] == "zeek").all() or not (frame["execution_mode"] == "docker").all() or synthetic.any():
            raise ValueError(f"{path}: некорректная provenance metadata")
        duplicates = seen_executions & set(frame["execution_id"])
        if duplicates:
            raise ValueError("Дубли execution_id: " + ", ".join(sorted(duplicates)))
        seen_executions.update(frame["execution_id"])
        validate_feature_frame(frame.drop(columns=[column for column in frame.columns if column not in ordered_features]), ordered_features)
        hashes[path.name] = sha256_file(path)
        frames.append(frame)
    return pd.concat(frames, ignore_index=True), hashes


def metrics(y_true: pd.Series, y_pred: np.ndarray) -> dict[str, Any]:
    labels = ["benign", *ATTACK_LABELS]
    precision, recall, f1, support = precision_recall_fscore_support(y_true, y_pred, labels=labels, zero_division=0)
    attack_true = y_true.isin(ATTACK_LABELS)
    attack_pred = np.isin(y_pred, ATTACK_LABELS)
    return {
        "accuracy": accuracy_score(y_true, y_pred),
        "balanced_accuracy": balanced_accuracy_score(y_true, y_pred),
        "macro_precision": precision_score(y_true, y_pred, average="macro", zero_division=0),
        "macro_recall": recall_score(y_true, y_pred, average="macro", zero_division=0),
        "macro_f1": f1_score(y_true, y_pred, average="macro", zero_division=0),
        "weighted_f1": f1_score(y_true, y_pred, average="weighted", zero_division=0),
        "attack_macro_recall": recall_score(y_true, y_pred, labels=list(ATTACK_LABELS), average="macro", zero_division=0),
        "attack_macro_f1": f1_score(y_true, y_pred, labels=list(ATTACK_LABELS), average="macro", zero_division=0),
        "collapsed_attack_precision": precision_score(attack_true, attack_pred, zero_division=0),
        "collapsed_attack_recall": recall_score(attack_true, attack_pred, zero_division=0),
        "collapsed_attack_f1": f1_score(attack_true, attack_pred, zero_division=0),
        "per_class": {label: {"precision": float(p), "recall": float(r), "f1": float(score), "support": int(count)} for label, p, r, score, count in zip(labels, precision, recall, f1, support)},
        "attacks_predicted_as_benign": int(((y_true.isin(ATTACK_LABELS)) & (y_pred == "benign")).sum()),
        "benign_predicted_as_attack": int(((y_true == "benign") & np.isin(y_pred, ATTACK_LABELS)).sum()),
    }


def evaluate_frozen(model: Any, frame: pd.DataFrame, ordered_features: list[str]) -> dict[str, Any]:
    x = validate_feature_frame(frame.loc[:, ordered_features], ordered_features)
    prediction = model.predict(x)
    result = metrics(frame["label"], prediction)
    result["rows"] = int(len(frame))
    result["class_distribution"] = dict(Counter(frame["label"]))
    return result


def evaluate_policy(metrics_by_group: dict[str, dict[str, Any]], overall: dict[str, Any], policy: dict[str, Any]) -> dict[str, Any]:
    groups: dict[str, bool] = {}
    for name, value in metrics_by_group.items():
        groups[name] = bool(
            value["macro_f1"] >= policy["minimum_group_macro_f1"]
            and value["per_class"]["benign"]["recall"] >= policy["minimum_group_benign_recall"]
            and value["attack_macro_recall"] >= policy["minimum_group_attack_macro_recall"]
        )
    passed = bool(
        all(groups.values())
        and overall["macro_f1"] >= policy["minimum_overall_macro_f1"]
        and overall["per_class"]["benign"]["recall"] >= policy["minimum_overall_benign_recall"]
        and overall["attack_macro_recall"] >= policy["minimum_overall_attack_macro_recall"]
        and overall["collapsed_attack_precision"] >= policy["minimum_collapsed_attack_precision"]
        and overall["collapsed_attack_recall"] >= policy["minimum_collapsed_attack_recall"]
    )
    return {"groups": groups, "environment_robustness_passed": passed}
