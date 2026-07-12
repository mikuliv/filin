from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import yaml


def main() -> None:
    parser = argparse.ArgumentParser(description="Post-hoc linear contributions for benign false positives.")
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--datasets-dir", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    manifest_path = Path(args.manifest)
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    features = list(manifest["ordered_feature_list"])
    model = joblib.load(manifest_path.parents[3] / manifest["artifact_path"])
    frame = pd.concat([pd.read_csv(path) for path in sorted(Path(args.datasets_dir).glob("windows_network_sensor_v0_3_run_v033_*.csv"))], ignore_index=True)
    x = frame.loc[:, features]
    transformed = model.named_steps["scale"].transform(model.named_steps["imputer"].transform(x))
    classifier = model.named_steps["model"]
    predictions = classifier.predict(x)
    index = {label: number for number, label in enumerate(classifier.classes_)}
    benign = index["benign"]
    aggregate: dict[str, list[float]] = defaultdict(list)
    records = []
    for row_index, (label, prediction) in enumerate(zip(frame.label, predictions)):
        if label != "benign" or prediction == "benign":
            continue
        predicted = index[prediction]
        delta = transformed[row_index] * (classifier.coef_[predicted] - classifier.coef_[benign])
        top = sorted(zip(features, delta.tolist()), key=lambda item: item[1], reverse=True)[:10]
        for feature, value in top:
            aggregate[feature].append(float(value))
        records.append({"run_id": frame.run_id.iloc[row_index], "benign_variant_id": frame.scenario_id.iloc[row_index], "predicted_class": prediction, "top_positive_contributions": [{"feature": feature, "contribution_margin": value} for feature, value in top]})
    frequent = sorted(({"feature": feature, "mean_positive_margin": float(np.mean(values)), "occurrences": len(values)} for feature, values in aggregate.items()), key=lambda item: (item["occurrences"], item["mean_positive_margin"]), reverse=True)
    result = {"false_positive_rows": len(records), "top_features": frequent[:20], "records": records}
    target = Path(args.output)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    summary = target.with_name("decision_contributions_summary.md")
    summary.write_text("# Вклады признаков v0.3.3\n\n" + "\n".join(f"- `{item['feature']}`: {item['occurrences']} false positives, mean margin {item['mean_positive_margin']:.6f}" for item in frequent[:20]) + "\n", encoding="utf-8")
    print(json.dumps({"false_positive_rows": len(records), "top_features": frequent[:5]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
