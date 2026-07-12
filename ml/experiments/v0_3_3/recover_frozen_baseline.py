"""Deterministically reconstruct the documented v0.3.1 sensor baseline.

Only recovered v0.3.1 source train datasets are accepted.  This tool never
reads v0.3.2/v0.3.3 data and exists to document reconstruction provenance when
the original serialized artifact is unavailable.
"""
from __future__ import annotations

import argparse
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


EXCLUDED = {
    "run_id", "label", "label_type", "scenario_id", "execution_id",
    "scenario_execution_key", "feature_profile", "observation_source",
    "sensor_type", "execution_mode", "synthetic",
}
ATTACKS = ["port_scan", "auth_failures", "web_probe", "low_rate_dos", "beacon_simulation"]


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def source_files(dataset_dir: Path, partition: str) -> list[Path]:
    files = sorted(dataset_dir.glob(f"windows_network_sensor_v0_3_run_v030_zeek_{partition}_*.csv"))
    expected = 6 if partition == "train" else 3
    if len(files) != expected:
        raise ValueError(f"Ожидалось {expected} v0.3.1 {partition} datasets, найдено {len(files)}.")
    return files


def feature_list(frame: pd.DataFrame) -> list[str]:
    return [column for column in frame.columns if column not in EXCLUDED and pd.api.types.is_numeric_dtype(frame[column])]


def build_pipeline() -> Pipeline:
    return Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("scale", StandardScaler()),
        ("model", LogisticRegression(max_iter=1000, class_weight="balanced", random_state=42)),
    ])


def main() -> None:
    parser = argparse.ArgumentParser(description="Deterministic recovery of frozen v0.3.1 baseline.")
    parser.add_argument("--dataset-dir", required=True)
    parser.add_argument("--source-report", required=True)
    parser.add_argument("--output-model", required=True)
    parser.add_argument("--output-manifest", required=True)
    args = parser.parse_args()
    dataset_dir = Path(args.dataset_dir)
    train_paths, test_paths = source_files(dataset_dir, "train"), source_files(dataset_dir, "test")
    train = pd.concat([pd.read_csv(path) for path in train_paths], ignore_index=True)
    test = pd.concat([pd.read_csv(path) for path in test_paths], ignore_index=True)
    if len(train) != 78 or len(test) != 39:
        raise ValueError(f"Неожиданный размер v0.3.1: train={len(train)}, test={len(test)}.")
    if set(train.run_id) != {f"run_v030_zeek_train_{index:03d}" for index in range(1, 7)}:
        raise ValueError("Состав source train runs не соответствует v0.3.1.")
    if not (train.feature_profile == "network_sensor_v0_3").all() or not (test.feature_profile == "network_sensor_v0_3").all():
        raise ValueError("Восстановление допускается только для network_sensor_v0_3.")
    features = feature_list(train)
    if features != feature_list(test):
        raise ValueError("Порядок model features train/test не совпадает.")
    model = build_pipeline()
    model.fit(train[features], train.label)
    prediction = model.predict(test[features])
    metrics = {
        "pooled_macro_f1": f1_score(test.label, prediction, average="macro", zero_division=0),
        "balanced_accuracy": balanced_accuracy_score(test.label, prediction),
        "attack_macro_recall": recall_score(test.label, prediction, labels=ATTACKS, average="macro", zero_division=0),
    }
    historical = json.loads(Path(args.source_report).read_text(encoding="utf-8"))["network_sensor_v0_3"]
    expected = {key: float(historical[key]) for key in metrics}
    if any(abs(metrics[key] - expected[key]) > 1e-12 for key in metrics):
        raise ValueError(f"Метрики reconstruction не совпали с v0.3.1: actual={metrics}, expected={expected}")
    output_model = Path(args.output_model)
    output_model.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, output_model)
    manifest = {
        "provenance_type": "deterministic_source_reconstruction",
        "model_reconstructed_from_source_train": True,
        "model_retrained_on_v033_data": False,
        "source_train_run_ids": sorted(train.run_id.unique().tolist()),
        "source_test_run_ids": sorted(test.run_id.unique().tolist()),
        "source_train_dataset_sha256": {path.name: file_hash(path) for path in train_paths},
        "source_test_dataset_sha256": {path.name: file_hash(path) for path in test_paths},
        "source_report_sha256": file_hash(Path(args.source_report)),
        "model_sha256": file_hash(output_model),
        "ordered_feature_list": features,
        "model_class": "LogisticRegression",
        "model_parameters": model.named_steps["model"].get_params(),
        "preprocessing": {"imputer": {"class": "SimpleImputer", "strategy": "median", "statistics": model.named_steps["imputer"].statistics_.tolist()}, "scaler": {"class": "StandardScaler", "mean": model.named_steps["scale"].mean_.tolist(), "scale": model.named_steps["scale"].scale_.tolist(), "var": model.named_steps["scale"].var_.tolist()}},
        "classes": model.named_steps["model"].classes_.tolist(),
        "n_features_in": int(model.named_steps["model"].n_features_in_),
        "verification": {"historical_metrics": expected, "reconstructed_metrics": metrics, "metrics_match": True},
    }
    output_manifest = Path(args.output_manifest)
    output_manifest.parent.mkdir(parents=True, exist_ok=True)
    output_manifest.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"model_sha256": manifest["model_sha256"], **metrics}, ensure_ascii=False))


if __name__ == "__main__":
    main()
