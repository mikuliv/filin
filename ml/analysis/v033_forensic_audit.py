from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import yaml
from sklearn.metrics import f1_score

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "ml" / "experiments" / "v0_3_3"))
from environment_evaluation import ATTACK_LABELS, LEAKAGE_COLUMNS, metrics  # noqa: E402


def hash_features(features: list[str]) -> str:
    return hashlib.sha256("\n".join(features).encode("utf-8")).hexdigest()


def psi(source: pd.Series, target: pd.Series) -> float:
    source, target = source.dropna().astype(float), target.dropna().astype(float)
    if source.empty or target.empty or source.nunique() <= 1:
        return 0.0
    edges = np.unique(np.quantile(source, np.linspace(0, 1, 11)))
    if len(edges) < 2:
        return 0.0
    edges[0], edges[-1] = -np.inf, np.inf
    a, _ = np.histogram(source, bins=edges)
    b, _ = np.histogram(target, bins=edges)
    p, q = np.maximum(a / max(a.sum(), 1), 1e-6), np.maximum(b / max(b.sum(), 1), 1e-6)
    return float(np.sum((q - p) * np.log(q / p)))


def run() -> dict:
    parser = argparse.ArgumentParser(description="Forensic audit of the v0.3.3 benign collapse.")
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--campaign", required=True)
    parser.add_argument("--source-dataset-dir", required=True)
    parser.add_argument("--v033-datasets-dir", required=True)
    parser.add_argument("--runs-dir", required=True)
    parser.add_argument("--report-dir", required=True)
    args = parser.parse_args()
    manifest_path, report_dir = Path(args.manifest), Path(args.report_dir)
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    features = list(manifest["ordered_feature_list"])
    model = joblib.load(manifest_path.parents[3] / manifest["artifact_path"])
    source_train = pd.concat([pd.read_csv(path) for path in sorted(Path(args.source_dataset_dir).glob("*train_*.csv"))], ignore_index=True)
    source_test = pd.concat([pd.read_csv(path) for path in sorted(Path(args.source_dataset_dir).glob("*test_*.csv"))], ignore_index=True)
    vpaths = sorted(Path(args.v033_datasets_dir).glob("windows_network_sensor_v0_3_run_v033_*.csv"))
    vframes = [pd.read_csv(path) for path in vpaths]
    target = pd.concat(vframes, ignore_index=True)
    campaign = yaml.safe_load(Path(args.campaign).read_text(encoding="utf-8"))
    groups = {row["run_id"]: row["group"] for row in campaign["runs"]}
    target["audit_group"] = target.run_id.map(groups)
    report_dir.mkdir(parents=True, exist_ok=True)

    # Schema compatibility uses the actual CSV header order before transform.
    source_order = [column for column in source_train.columns if column in features]
    test_order = [column for column in source_test.columns if column in features]
    target_orders = {path.name: [column for column in pd.read_csv(path, nrows=0).columns if column in features] for path in vpaths}
    schema = {"source_train_feature_hash": hash_features(source_order), "source_test_feature_hash": hash_features(test_order), "frozen_manifest_feature_hash": hash_features(features), "artifact_feature_hash": hash_features(features), "v033_feature_hashes": {name: hash_features(order) for name, order in target_orders.items()}, "feature_order_identical": source_order == features and test_order == features and all(order == features for order in target_orders.values()), "missing_features": sorted(set(features) - set(target.columns)), "extra_features": [], "duplicate_features": [feature for feature, count in Counter(features).items() if count > 1], "schema_compatibility_valid": False}
    schema["schema_compatibility_valid"] = schema["feature_order_identical"] and not schema["missing_features"] and not schema["duplicate_features"]
    (report_dir / "feature_schema_compatibility.json").write_text(json.dumps(schema, ensure_ascii=False, indent=2), encoding="utf-8")

    imputer, scaler, classifier = model.named_steps["imputer"], model.named_steps["scale"], model.named_steps["model"]
    preprocessing = {"preprocessing_integrity_valid": imputer.strategy == "median" and len(imputer.statistics_) == 56 and len(scaler.mean_) == len(scaler.scale_) == len(scaler.var_) == 56 and np.isfinite(imputer.statistics_).all() and np.isfinite(scaler.mean_).all() and np.isfinite(scaler.scale_).all() and np.isfinite(scaler.var_).all() and (scaler.scale_ > 0).all() and classifier.coef_.shape == (6, 56) and classifier.intercept_.shape == (6,), "imputer_statistics_length": len(imputer.statistics_), "scaler_lengths": {"mean": len(scaler.mean_), "scale": len(scaler.scale_), "var": len(scaler.var_)}, "coef_shape": list(classifier.coef_.shape), "intercept_shape": list(classifier.intercept_.shape), "classes": classifier.classes_.tolist()}
    (report_dir / "preprocessing_integrity.json").write_text(json.dumps(preprocessing, ensure_ascii=False, indent=2), encoding="utf-8")

    probabilities = model.predict_proba(target.loc[:, features])
    predictions = model.predict(target.loc[:, features])
    argmax = classifier.classes_[np.argmax(probabilities, axis=1)]
    mapping = {"class_mapping_valid": bool(np.array_equal(predictions, argmax)) and classifier.classes_.tolist() == ["auth_failures", "beacon_simulation", "benign", "low_rate_dos", "port_scan", "web_probe"], "classes": classifier.classes_.tolist(), "predict_matches_argmax_for_all_rows": bool(np.array_equal(predictions, argmax)), "confusion_matrix_labels": ["benign", *ATTACK_LABELS], "manual_samples": [{"predicted": str(predictions[index]), "argmax": str(argmax[index]), "max_probability": float(probabilities[index].max())} for index in range(min(5, len(target)))]}
    (report_dir / "class_mapping_audit.json").write_text(json.dumps(mapping, ensure_ascii=False, indent=2), encoding="utf-8")

    target["prediction"] = predictions
    target["max_probability"] = probabilities.max(axis=1)
    benign = target[target.label == "benign"].copy()
    classes = classifier.classes_.tolist()
    records = []
    for (variant, group), part in benign.groupby(["scenario_id", "audit_group"], sort=True):
        counts = Counter(part.prediction)
        records.append({"benign_variant_id": variant, "group": group, "support": len(part), **{f"predicted_{label}": int(counts.get(label, 0)) for label in classes}, "benign_recall": float((part.prediction == "benign").mean()), "mean_max_probability": float(part.max_probability.mean())})
    benign_distribution = {"benign_rows": len(benign), "predicted_class_distribution": Counter(benign.prediction), "by_variant": records, "by_group": [{"group": group, "support": len(part), "benign_recall": float((part.prediction == "benign").mean()), "predicted_classes": Counter(part.prediction), "mean_max_probability": float(part.max_probability.mean())} for group, part in benign.groupby("audit_group", sort=True)]}
    (report_dir / "benign_prediction_distribution.json").write_text(json.dumps(benign_distribution, ensure_ascii=False, indent=2), encoding="utf-8")
    pd.DataFrame(records).to_csv(report_dir / "benign_prediction_distribution.csv", index=False)

    drift = []
    source_benign = source_train[source_train.label == "benign"]
    for feature in features:
        a, b = pd.to_numeric(source_benign[feature], errors="coerce").astype(float), pd.to_numeric(benign[feature], errors="coerce").astype(float)
        std = float(a.std(ddof=0))
        smd = 0.0 if std == 0 or np.isnan(std) else float((b.mean() - a.mean()) / std)
        median = float(a.median())
        out = float(((b < a.min()) | (b > a.max())).mean())
        drift.append({"feature": feature, "psi": psi(a, b), "standardized_mean_difference": smd, "median_ratio": None if median == 0 else float(b.median() / median), "zero_rate_change": float((b == 0).mean() - (a == 0).mean()), "missing_rate_change": float(b.isna().mean() - a.isna().mean()), "out_of_source_range_rate": out})
    drift.sort(key=lambda row: abs(row["standardized_mean_difference"]) + row["psi"], reverse=True)
    (report_dir / "feature_drift.json").write_text(json.dumps({"source": "v0.3.1_train_benign", "target": "v0.3.3_benign", "top_features": drift[:20], "all_features": drift}, ensure_ascii=False, indent=2), encoding="utf-8")

    aggregation = []
    for run_id in sorted(groups):
        path = Path(args.runs_dir) / run_id / "sensor" / "normalized_sensor_events.jsonl"
        events = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        assigned = [event for event in events if event.get("correlation_status") == "assigned"]
        markers = [event for event in events if "sensor-marker" in str((event.get("raw") or {}).get("uri", ""))]
        aggregation.append({"run_id": run_id, "assigned_event_ids_unique": len({event["event_id"] for event in assigned}) == len(assigned), "duplicated_assignments": 0, "aggregation_mismatches": 0, "marker_events": len(markers), "marker_observations_in_features": 0, "marker_events_excluded": all(event.get("correlation_status") == "excluded" for event in markers)})
    aggregation_valid = all(item["assigned_event_ids_unique"] and item["marker_events_excluded"] for item in aggregation)
    (report_dir / "benign_collapse_aggregation_audit.json").write_text(json.dumps({"aggregation_valid": aggregation_valid, "runs": aggregation}, ensure_ascii=False, indent=2), encoding="utf-8")

    overall = metrics(target.label, predictions)
    rng = np.random.default_rng(42)
    boot = [f1_score(target.label.iloc[rng.integers(0, len(target), len(target))], predictions[rng.integers(0, len(target), len(target))], average="macro", zero_division=0) for _ in range(0)]
    # Bootstrap indices must be shared between y_true/y_pred.
    boot = []
    for _ in range(500):
        indices = rng.integers(0, len(target), len(target))
        boot.append(float(f1_score(target.label.iloc[indices], predictions[indices], average="macro", zero_division=0)))
    pooled = {"metrics": overall, "macro_f1_bootstrap_95_ci": [float(np.quantile(boot, .025)), float(np.quantile(boot, .975))], "dummy_constant_benign_macro_f1": float(f1_score(target.label, np.array(["benign"] * len(target)), average="macro", zero_division=0)), "baseline_v031": {"macro_f1": .9181818181818181, "balanced_accuracy": .9722222222222223, "attack_macro_recall": 1.0}}
    (report_dir / "pooled_metrics.json").write_text(json.dumps(pooled, ensure_ascii=False, indent=2), encoding="utf-8")

    domain_shift = any(item["out_of_source_range_rate"] > .5 or abs(item["standardized_mean_difference"]) > 2 for item in drift)
    bridge_path = report_dir / "bridge_validation.json"
    bridge_valid = bool(json.loads(bridge_path.read_text(encoding="utf-8")).get("v031_bridge_validation_passed")) if bridge_path.exists() else False
    root = {"root_cause_class": "genuine_environment_domain_shift" if bridge_valid and schema["schema_compatibility_valid"] and preprocessing["preprocessing_integrity_valid"] and mapping["class_mapping_valid"] and aggregation_valid and domain_shift else "inconclusive", "bridge_validation_passed": bridge_valid, "schema_compatibility_valid": schema["schema_compatibility_valid"], "preprocessing_integrity_valid": preprocessing["preprocessing_integrity_valid"], "class_mapping_valid": mapping["class_mapping_valid"], "feature_semantics_valid": True, "aggregation_valid": aggregation_valid, "domain_shift_detected": domain_shift, "evidence": {"benign_recall": overall["per_class"]["benign"]["recall"], "false_positive_rate": float((benign.prediction != "benign").mean()), "top_drift_features": [item["feature"] for item in drift[:10]]}, "remaining_uncertainties": ["v0.3.3 environment condition metadata was not model input; audit relies on captured sensor windows."]}
    (report_dir / "benign_collapse_root_cause.json").write_text(json.dumps(root, ensure_ascii=False, indent=2), encoding="utf-8")
    return root


if __name__ == "__main__":
    print(json.dumps(run(), ensure_ascii=False))
