"""Prospective v0.4 dataset-quality audit; it never rewrites historical data."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from schema import NETWORK_SENSOR_V0_4


def audit(path: Path, zero_feature_threshold: float = 0.5) -> dict:
    frame = pd.read_csv(path)
    missing = sorted(set(NETWORK_SENSOR_V0_4) - set(frame.columns))
    stats = {}
    for feature in NETWORK_SENSOR_V0_4:
        values = pd.to_numeric(frame[feature], errors="coerce") if feature in frame else pd.Series(dtype=float)
        stats[feature] = {"missing_rate": float(values.isna().mean()), "zero_rate": float(values.eq(0).mean()), "cardinality": int(values.nunique(dropna=True)), "min": None if values.dropna().empty else float(values.min()), "max": None if values.dropna().empty else float(values.max()), "constant": bool(values.nunique(dropna=True) <= 1)}
    suspicious = sorted(feature for feature, item in stats.items() if item["constant"] or item["zero_rate"] >= zero_feature_threshold)
    return {"feature_count": len(NETWORK_SENSOR_V0_4), "missing_features": missing, "constant_feature_rate": sum(item["constant"] for item in stats.values()) / len(stats), "all_zero_feature_rate": sum(item["zero_rate"] == 1 for item in stats.values()) / len(stats), "suspicious_features": suspicious, "valid": not missing and not suspicious, "features": stats}


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--report", required=True)
    args = parser.parse_args()
    result = audit(Path(args.dataset))
    Path(args.report).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    if not result["valid"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
