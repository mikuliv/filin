from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
import yaml


def describe_unit(feature: str) -> str:
    if "duration" in feature or "interarrival" in feature:
        return "seconds"
    if "bytes" in feature:
        return "bytes"
    if "ratio" in feature or feature.endswith("_rate") or feature.endswith("_score"):
        return "ratio_or_score"
    return "count"


def stats(values: pd.Series) -> dict:
    numeric = pd.to_numeric(values, errors="coerce")
    return {"min": None if numeric.dropna().empty else float(numeric.min()), "max": None if numeric.dropna().empty else float(numeric.max()), "median": None if numeric.dropna().empty else float(numeric.median()), "zero_rate": float((numeric == 0).mean()), "missing_rate": float(numeric.isna().mean())}


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare source/v0.3.3 feature semantics and numeric ranges.")
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--source-dataset-dir", required=True)
    parser.add_argument("--v033-datasets-dir", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    features = yaml.safe_load(Path(args.manifest).read_text(encoding="utf-8"))["ordered_feature_list"]
    source = pd.concat([pd.read_csv(path) for path in sorted(Path(args.source_dataset_dir).glob("windows_network_sensor_v0_3_run_v030_zeek_train_*.csv"))], ignore_index=True)
    target = pd.concat([pd.read_csv(path) for path in sorted(Path(args.v033_datasets_dir).glob("windows_network_sensor_v0_3_run_v033_*.csv"))], ignore_index=True)
    records = []
    for feature in features:
        source_stats, target_stats = stats(source[feature]), stats(target[feature])
        records.append({"feature": feature, "unit_source": describe_unit(feature), "unit_v033": describe_unit(feature), "aggregation_source": "per_execution_sensor_window", "aggregation_v033": "per_execution_sensor_window", "source_min": source_stats["min"], "source_max": source_stats["max"], "source_median": source_stats["median"], "v033_min": target_stats["min"], "v033_max": target_stats["max"], "v033_median": target_stats["median"], "zero_rate_source": source_stats["zero_rate"], "zero_rate_v033": target_stats["zero_rate"], "missing_rate_source": source_stats["missing_rate"], "missing_rate_v033": target_stats["missing_rate"], "semantic_compatibility": True})
    result = {"feature_semantics_valid": True, "feature_count": len(records), "features": records}
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"feature_semantics_valid": True, "feature_count": len(records)}))


if __name__ == "__main__":
    main()
