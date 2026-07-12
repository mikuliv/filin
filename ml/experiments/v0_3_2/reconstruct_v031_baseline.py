"""Deterministically reconstruct the v0.3.1 baseline from source train data.

This is intentionally separate from external evaluation.  It is the only
v0.3.2 entry point allowed to call ``fit`` and it rejects non-v0.3.1 inputs.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import joblib
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import balanced_accuracy_score, f1_score, recall_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


ATTACKS = ["port_scan", "auth_failures", "web_probe", "low_rate_dos", "beacon_simulation"]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return digest


def reconstruct(train_paths: list[Path], test_paths: list[Path], features: list[str], artifact_path: Path) -> dict:
    if any("run_v030_zeek_train_" not in path.name for path in train_paths):
        raise ValueError("Reconstruction accepts only v0.3.1 source train datasets")
    train = pd.concat([pd.read_csv(path) for path in train_paths], ignore_index=True)
    test = pd.concat([pd.read_csv(path) for path in test_paths], ignore_index=True)
    model = Pipeline([("imputer", SimpleImputer(strategy="median")), ("scale", StandardScaler()), ("model", LogisticRegression(max_iter=1000, class_weight="balanced", random_state=42))])
    model.fit(train.loc[:, features], train["label"])
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, artifact_path)
    prediction = model.predict(test.loc[:, features])
    return {"model_reconstructed_from_source_train": True, "model_retrained_on_robustness_data": False, "artifact_sha256": _sha256(artifact_path), "source_train_dataset_sha256": {path.name: _sha256(path) for path in train_paths}, "historical_test_metrics": {"macro_f1": float(f1_score(test.label, prediction, average="macro", zero_division=0)), "balanced_accuracy": float(balanced_accuracy_score(test.label, prediction)), "attack_macro_recall": float(recall_score(test.label, prediction, labels=ATTACKS, average="macro", zero_division=0))}}
