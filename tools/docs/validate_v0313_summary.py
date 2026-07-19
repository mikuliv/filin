"""Строгая проверка полноты итогового отчёта v0.3.13."""
from __future__ import annotations
import argparse, json
from pathlib import Path

SECTIONS = ["Назначение этапа","Научная гипотеза","Frozen candidate","Previous-stage integrity","Protocol freeze","Campaign freeze","Blind design","Environmental shift design","Scenario independence","Safety policy","Holdout runs","Seeds","Episode design","Episode-length balance","Attack-class balance","Benign variants","Environmental groups","Docker isolation","Capture collection","Capture lock","Zeek processing","Feature extraction","Feature schema","Causal feature audit","Row identity","Activity key","Episode structure","Holdout input lock","Label vault","Blind access audit","No-fit audit","Regression bundle pre-manifest","Immutable prediction","Prediction integrity","Causal-order invariance","Window metrics","Stateful metrics","Episode metrics","Detection latency","Per-class metrics","Per-group metrics","Per-run metrics","Per-variant metrics","Per-length metrics","Calibration","Conformal","Controls","Drift","Failure analysis","Bootstrap intervals","Hardware","Performance profile","Collection performance","Zeek performance","Feature performance","Prediction performance","CPU and RAM","GPU applicability","Checkpoint and resume","Regression bundle","Bundle validation","Holdout policy result","Readiness for v0.3.14","Limitations","Next stage","Conclusion"]

def main():
    p=argparse.ArgumentParser(); p.add_argument("--summary",required=True,type=Path); p.add_argument("--strict",action="store_true"); a=p.parse_args()
    text=a.summary.read_text(encoding="utf-8"); missing=[x for x in SECTIONS if f"## {x}" not in text]
    report=a.summary.parent; required=["protocol_freeze.json","campaign_integrity.json","capture_lock.json","feature_integrity.json","holdout_input_lock.json","blind_access_audit.json","no_fit_audit.json","immutable_prediction_manifest.json","causal_order_invariance.json","window_metrics.json","stateful_metrics.json","episode_metrics.json","bootstrap_intervals.json","regression_bundle_validation.json","v0_3_13_policy_result.json"]
    missing_files=[x for x in required if not (report/x).is_file()]
    policy=json.loads((report/"v0_3_13_policy_result.json").read_text(encoding="utf-8"))
    valid=not missing and not missing_files and policy.get("v0313_holdout_completed") is True
    print(json.dumps({"valid":valid,"missing_sections":missing,"missing_files":missing_files},ensure_ascii=False,indent=2))
    return 0 if valid else 1
if __name__=="__main__": raise SystemExit(main())
