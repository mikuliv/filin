from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import joblib
import pandas as pd
import yaml
from sklearn.metrics import confusion_matrix

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "ml" / "experiments" / "v0_3_3"))
from environment_evaluation import ATTACK_LABELS, metrics  # noqa: E402


def feature_hash(features: list[str]) -> str:
    return hashlib.sha256("\n".join(features).encode("utf-8")).hexdigest()


def run_bridge(manifest_path: Path, source_dataset_dir: Path, historical_report: Path) -> dict:
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    features = list(manifest["ordered_feature_list"])
    paths = sorted(source_dataset_dir.glob("windows_network_sensor_v0_3_run_v030_zeek_test_*.csv"))
    frame = pd.concat([pd.read_csv(path) for path in paths], ignore_index=True)
    model = joblib.load(manifest_path.parents[3] / manifest["artifact_path"])
    prediction = model.predict(frame.loc[:, features])
    actual = metrics(frame.label, prediction)
    historical = json.loads(historical_report.read_text(encoding="utf-8"))["network_sensor_v0_3"]
    expected = {key: float(historical[key]) for key in ("pooled_macro_f1", "balanced_accuracy", "attack_macro_recall")}
    measured = {"pooled_macro_f1": actual["macro_f1"], "balanced_accuracy": actual["balanced_accuracy"], "attack_macro_recall": actual["attack_macro_recall"]}
    deltas = {key: measured[key] - expected[key] for key in expected}
    return {
        "source_test_rows": len(frame),
        "feature_count": len(features),
        "ordered_feature_hash": feature_hash(features),
        "classes": model.named_steps["model"].classes_.tolist(),
        "predictions": prediction.tolist(),
        "confusion_matrix_labels": ["benign", *ATTACK_LABELS],
        "confusion_matrix": confusion_matrix(frame.label, prediction, labels=["benign", *ATTACK_LABELS]).tolist(),
        "metrics": measured,
        "historical_metrics": expected,
        "metric_deltas": deltas,
        "v031_bridge_validation_passed": all(abs(value) <= 1e-12 for value in deltas.values()),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Bridge validation through the v0.3.3 frozen evaluation path.")
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--source-dataset-dir", required=True)
    parser.add_argument("--historical-report", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    result = run_bridge(Path(args.manifest), Path(args.source_dataset_dir), Path(args.historical_report))
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))
    if not result["v031_bridge_validation_passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
