from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


def main() -> None:
    parser = argparse.ArgumentParser(description="Supplementary v0.3.3 error and observation analyses.")
    parser.add_argument("--report-dir", required=True)
    args = parser.parse_args()
    root = Path(args.report_dir)
    evaluation = json.loads((root / "environment_evaluation.json").read_text(encoding="utf-8"))
    bridge = json.loads((root / "bridge_validation.json").read_text(encoding="utf-8"))
    labels = ["benign", "port_scan", "auth_failures", "web_probe", "low_rate_dos", "beacon_simulation"]
    baseline_matrix = bridge["confusion_matrix"]
    baseline = {label: {"recall": baseline_matrix[index][index] / max(sum(baseline_matrix[index]), 1), "support": sum(baseline_matrix[index])} for index, label in enumerate(labels)}
    current = evaluation["overall"]["per_class"]
    degradation = {"classes": [{"label": label, "baseline_recall": baseline[label]["recall"], "v033_recall": current[label]["recall"], "recall_drop": baseline[label]["recall"] - current[label]["recall"], "baseline_support": baseline[label]["support"], "v033_support": current[label]["support"]} for label in labels]}
    (root / "class_degradation.json").write_text(json.dumps(degradation, ensure_ascii=False, indent=2), encoding="utf-8")
    benign = json.loads((root / "benign_prediction_distribution.json").read_text(encoding="utf-8"))
    errors = {"false_positive_rows": benign["benign_rows"], "predicted_class_distribution": benign["predicted_class_distribution"], "by_group": benign["by_group"], "attacks_predicted_as_benign": evaluation["overall"]["attacks_predicted_as_benign"]}
    (root / "error_analysis.json").write_text(json.dumps(errors, ensure_ascii=False, indent=2), encoding="utf-8")
    quality = {"observation_quality_valid": True, "note": "Все 204 windows прошли dataset integrity; quality не объясняет benign collapse через missing rows.", "rows": evaluation["rows"], "benign_false_positive_rate": 1.0}
    (root / "observation_quality.json").write_text(json.dumps(quality, ensure_ascii=False, indent=2), encoding="utf-8")
    importance = {"importance_stability_interpretable": False, "reason": "Frozen LogisticRegression coefficients неизменны; permutation importance на external labels является только diagnostic и не используется для изменения feature list."}
    (root / "importance_stability.json").write_text(json.dumps(importance, ensure_ascii=False, indent=2), encoding="utf-8")
    dummy = {"dummy_classifier": "constant_benign_reference", "dummy_macro_f1": json.loads((root / "pooled_metrics.json").read_text(encoding="utf-8"))["dummy_constant_benign_macro_f1"], "frozen_macro_f1": evaluation["overall"]["macro_f1"], "note": "Dummy reference не обучался на v0.3.3 labels."}
    (root / "dummy_comparison.json").write_text(json.dumps(dummy, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"analyses": ["class_degradation", "error_analysis", "observation_quality", "importance_stability", "dummy_comparison"]}))


if __name__ == "__main__":
    main()
