"""Однократная validation frozen v0.3.4 candidate без fit/refit."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import joblib
import numpy as np
import yaml

ROOT = Path(__file__).resolve().parents[3]
import sys
sys.path.insert(0, str(ROOT / "ml" / "training"))
from run_v0_3_4_model_selection import metrics
from v034_dataset_loader import load_v034_dataset
from v034_data_access import load_policy

FORBIDDEN = ("fit(", "partial_fit(", "set_params(")


def validate(manifest_path: Path, artifact_path: Path, datasets: list[Path], access_path: Path, policy_path: Path) -> dict:
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    if not manifest.get("prohibit_refit_on_validation"):
        raise ValueError("Manifest не запрещает refit на validation")
    access = load_policy(access_path)
    X, y, groups, metadata = load_v034_dataset(datasets, access, manifest["feature_profile"])
    if list(X.columns) != manifest["ordered_feature_list"]:
        raise ValueError("Схема validation не соответствует frozen artifact")
    model = joblib.load(artifact_path)
    predicted = model.predict(X)  # only prediction: no fit, tuning or calibration
    result = metrics(y.to_numpy(), predicted, metadata)
    result.update({"v034_internal_validation_completed": True, "validation_run_ids": sorted(groups.unique()), "per_group": {}})
    for group in sorted(groups.unique()):
        mask = groups == group; result["per_group"][group] = metrics(y[mask].to_numpy(), predicted[mask.to_numpy()], metadata[mask])
    rules = yaml.safe_load(policy_path.read_text(encoding="utf-8"))["model_selection_policy"]["internal_validation_policy"]
    aliases = {"minimum_macro_f1": "macro_f1", "minimum_balanced_accuracy": "balanced_accuracy", "minimum_benign_recall": "benign_recall", "maximum_false_positive_rate": "false_positive_rate", "minimum_hard_negative_benign_recall": "hard_negative_benign_recall", "minimum_attack_macro_recall": "attack_macro_recall", "minimum_collapsed_attack_precision": "collapsed_attack_precision", "minimum_collapsed_attack_recall": "collapsed_attack_recall"}
    flags = {rule: result[metric] >= threshold if rule.startswith("minimum") else result[metric] <= threshold for rule, metric in aliases.items() for threshold in [rules[rule]]}
    if rules.get("prohibit_zero_recall_class"):
        flags["prohibit_zero_recall_class"] = all(value > 0 for value in result["per_group"].values())
    result["policy_flags"] = flags; result["v034_internal_validation_passed"] = all(flags.values()); result["candidate_ready_for_v035"] = result["v034_internal_validation_passed"]
    return result


def main() -> None:
    parser=argparse.ArgumentParser(); parser.add_argument("--manifest", required=True); parser.add_argument("--artifact", required=True); parser.add_argument("--datasets", nargs="+", required=True); parser.add_argument("--data-access-policy", required=True); parser.add_argument("--policy", required=True); parser.add_argument("--output", required=True); args=parser.parse_args()
    value=validate(Path(args.manifest),Path(args.artifact),[Path(x) for x in args.datasets],Path(args.data_access_policy),Path(args.policy)); Path(args.output).parent.mkdir(parents=True,exist_ok=True);Path(args.output).write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding="utf-8")
if __name__ == "__main__": main()
