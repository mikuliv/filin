"""Ограниченный selection v0.3.4 с StratifiedGroupKFold только по train-run."""
from __future__ import annotations

import argparse
import itertools
import json
import time
from pathlib import Path
from typing import Any

import numpy as np
import yaml
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import balanced_accuracy_score, f1_score, precision_recall_fscore_support, precision_score, recall_score
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from v034_dataset_loader import load_v034_dataset
from v034_data_access import load_policy

MODELS = {"LogisticRegression": LogisticRegression, "RandomForestClassifier": RandomForestClassifier, "HistGradientBoostingClassifier": HistGradientBoostingClassifier}


def _collapsed(y: np.ndarray) -> np.ndarray:
    return np.where(y == "benign", "benign", "attack")


def metrics(y_true: np.ndarray, y_pred: np.ndarray, metadata=None) -> dict[str, float]:
    labels = sorted(set(y_true) | set(y_pred))
    recalls = dict(zip(labels, precision_recall_fscore_support(y_true, y_pred, labels=labels, zero_division=0)[1]))
    benign_recall = recalls.get("benign", 0.0)
    benign_mask = y_true == "benign"
    hard_mask = benign_mask & metadata.get("scenario_id", "").astype(str).isin(["benign_database_pool_recovery", "benign_multi_service_health", "benign_long_poll_keepalive", "benign_mirror_sync_burst"]).to_numpy() if metadata is not None else np.zeros(len(y_true), bool)
    attack_labels = [label for label in labels if label != "benign"]
    attack_recall = float(np.mean([recalls.get(label, 0.0) for label in attack_labels])) if attack_labels else 0.0
    actual, predicted = _collapsed(y_true), _collapsed(y_pred)
    return {
        "macro_f1": float(f1_score(y_true, y_pred, average="macro", zero_division=0)),
        "balanced_accuracy": float(balanced_accuracy_score(y_true, y_pred)),
        "benign_recall": float(benign_recall),
        "false_positive_rate": float(np.mean(y_pred[benign_mask] != "benign")) if benign_mask.any() else 0.0,
        "hard_negative_benign_recall": float(np.mean(y_pred[hard_mask] == "benign")) if hard_mask.any() else benign_recall,
        "attack_macro_recall": attack_recall,
        "collapsed_attack_precision": float(precision_score(actual, predicted, pos_label="attack", zero_division=0)),
        "collapsed_attack_recall": float(recall_score(actual, predicted, pos_label="attack", zero_division=0)),
    }


def build_pipeline(spec: dict[str, Any], params: dict[str, Any]) -> Pipeline:
    estimator = MODELS[spec["class"]](**{**spec.get("parameters", {}), **params})
    steps: list[tuple[str, Any]] = [("imputer", SimpleImputer(strategy="median"))]
    if "StandardScaler" in spec.get("preprocessing", []):
        steps.append(("scaler", StandardScaler()))
    steps.append(("model", estimator))
    return Pipeline(steps)


def candidate_configs(policy: dict[str, Any]):
    root = policy["model_selection_policy"]
    for profile, names in root["matrix"].items():
        for name in names:
            spec = root["candidates"][name]
            keys, values = zip(*spec.get("grid", {}).items()) if spec.get("grid") else ((), ())
            for combination in itertools.product(*values) if values else [()]:
                yield profile, name, spec, dict(zip(keys, combination))


def evaluate_candidate(X, y, groups, metadata, spec, params, n_splits=6) -> dict[str, Any]:
    cv = StratifiedGroupKFold(n_splits=n_splits, shuffle=True, random_state=42)
    oof = np.empty(len(y), dtype=object); folds = []
    for number, (train_idx, test_idx) in enumerate(cv.split(X, y, groups), 1):
        if set(groups.iloc[train_idx]) & set(groups.iloc[test_idx]):
            raise RuntimeError("run_id одновременно попал в train и fold validation")
        pipe = build_pipeline(spec, params); started = time.perf_counter(); pipe.fit(X.iloc[train_idx], y.iloc[train_idx]); fit_time = time.perf_counter() - started
        started = time.perf_counter(); predicted = pipe.predict(X.iloc[test_idx]); predict_time = time.perf_counter() - started
        oof[test_idx] = predicted
        fold = metrics(y.iloc[test_idx].to_numpy(), predicted, metadata.iloc[test_idx])
        fold.update({"fold": number, "fit_time": fit_time, "predict_time": predict_time, "train_run_ids": sorted(set(groups.iloc[train_idx])), "validation_run_ids": sorted(set(groups.iloc[test_idx]))})
        folds.append(fold)
    pooled = metrics(y.to_numpy(), oof, metadata)
    pooled.update({"folds": folds, "macro_f1_std": float(np.std([fold["macro_f1"] for fold in folds])), "worst_fold_benign_recall": min(fold["benign_recall"] for fold in folds), "worst_fold_attack_macro_recall": min(fold["attack_macro_recall"] for fold in folds)})
    return pooled


def policy_flags(result: dict[str, float], policy: dict[str, Any]) -> dict[str, bool]:
    root = policy["model_selection_policy"]
    flags = {name: result.get(name, 0) >= value for name, value in root["minimum_cv_metrics"].items()}
    flags.update({name: result.get(name, float("inf")) <= value for name, value in root["maximum_cv_metrics"].items()})
    return flags


def select(results: list[dict[str, Any]], policy: dict[str, Any]) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    passing = []
    for result in results:
        result["policy_flags"] = policy_flags(result["metrics"], policy)
        result["cv_passed"] = all(result["policy_flags"].values())
        if result["cv_passed"]: passing.append(result)
    rank = {"logistic_regression": 0, "random_forest": 1, "hist_gradient_boosting": 2}
    passing.sort(key=lambda item: (-item["metrics"]["macro_f1"], -item["metrics"]["benign_recall"], -item["metrics"]["collapsed_attack_precision"], item["metrics"]["macro_f1_std"], item["feature_count"], rank[item["model"]]))
    return (passing[0] if passing else None), results


def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("--datasets", nargs="+", required=True); parser.add_argument("--policy", required=True); parser.add_argument("--data-access-policy", required=True); parser.add_argument("--output", required=True); args = parser.parse_args()
    policy = yaml.safe_load(Path(args.policy).read_text(encoding="utf-8")); access = load_policy(Path(args.data_access_policy)); results=[]
    for profile, name, spec, params in candidate_configs(policy):
        X, y, groups, metadata = load_v034_dataset([Path(path) for path in args.datasets], access, profile)
        result = {"candidate_id": f"{profile}:{name}:{json.dumps(params, sort_keys=True)}", "profile": profile, "model": name, "parameters": params, "feature_count": X.shape[1], "metrics": evaluate_candidate(X, y, groups, metadata, spec, params)}; results.append(result)
    chosen, results = select(results, policy); output={"v034_cv_completed": True, "v034_cv_passed": chosen is not None, "candidate": chosen, "candidates": results, "validation_dataset_loaded": False}; Path(args.output).parent.mkdir(parents=True, exist_ok=True); Path(args.output).write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")

if __name__ == "__main__": main()
