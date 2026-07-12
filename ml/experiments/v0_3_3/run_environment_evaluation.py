"""External evaluation of the recovered, frozen v0.3.1 sensor baseline.

No estimator in this module is fitted.  The only model operation is loading a
trusted recovered artifact and calling ``predict`` on v0.3.3 sensor windows.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import joblib
import pandas as pd
import yaml

from environment_evaluation import evaluate_frozen, evaluate_policy, load_policy


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_manifest(path: Path) -> dict:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    required = {"artifact_path", "model_sha256", "ordered_feature_list", "prohibit_v033_fit"}
    missing = required - set(data)
    if missing or not data["prohibit_v033_fit"]:
        raise ValueError("Frozen model manifest не подтверждает режим без fit.")
    return data


def verify_model(model: object, features: list[str]) -> None:
    named = getattr(model, "named_steps", {})
    if set(named) != {"imputer", "scale", "model"}:
        raise ValueError("Frozen artifact должен содержать imputer, scale и model.")
    if named["imputer"].strategy != "median" or named["model"].__class__.__name__ != "LogisticRegression":
        raise ValueError("Frozen artifact не соответствует v0.3.1 LogisticRegression pipeline.")
    if int(named["model"].n_features_in_) != len(features):
        raise ValueError("Число features artifact и manifest не совпадает.")


def main() -> None:
    parser = argparse.ArgumentParser(description="External frozen evaluation for v0.3.3 environment data.")
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--campaign", required=True)
    parser.add_argument("--datasets-dir", required=True)
    parser.add_argument("--policy", required=True)
    parser.add_argument("--report-dir", required=True)
    args = parser.parse_args()
    manifest_path, campaign_path, datasets_dir, report_dir = map(Path, (args.manifest, args.campaign, args.datasets_dir, args.report_dir))
    manifest = load_manifest(manifest_path)
    model_path = manifest_path.parents[3] / manifest["artifact_path"]
    if sha256(model_path) != manifest["model_sha256"]:
        raise ValueError("SHA-256 frozen artifact не совпадает с manifest.")
    model = joblib.load(model_path)
    features = list(manifest["ordered_feature_list"])
    verify_model(model, features)
    campaign = yaml.safe_load(campaign_path.read_text(encoding="utf-8"))
    groups = {run["run_id"]: run["group"] for run in campaign["runs"]}
    paths = sorted(datasets_dir.glob("windows_network_sensor_v0_3_run_v033_*.csv"))
    if len(paths) != 12 or {path.stem.removeprefix("windows_network_sensor_v0_3_") for path in paths} != set(groups):
        raise ValueError("Нужны ровно 12 datasets v0.3.3 из campaign manifest.")
    frames = [pd.read_csv(path) for path in paths]
    per_run = {}
    per_group_frames: dict[str, list[pd.DataFrame]] = {}
    for frame in frames:
        run_id = str(frame.run_id.iloc[0])
        if len(frame) != 17:
            raise ValueError(f"{run_id}: ожидается 17 sensor windows.")
        per_run[run_id] = evaluate_frozen(model, frame, features)
        per_group_frames.setdefault(groups[run_id], []).append(frame)
    per_group = {group: evaluate_frozen(model, pd.concat(group_frames, ignore_index=True), features) for group, group_frames in per_group_frames.items()}
    combined = pd.concat(frames, ignore_index=True)
    overall = evaluate_frozen(model, combined, features)
    policy, policy_sha = load_policy(Path(args.policy))
    policy_result = evaluate_policy(per_group, overall, policy)
    output = {
        "frozen_model_integrity_valid": True,
        "model_retrained_on_v033_data": False,
        "feature_list_changed": False,
        "preprocessing_changed": False,
        "threshold_changed": False,
        "external_environment_evaluation_completed": True,
        "rows": int(len(combined)),
        "class_distribution": overall["class_distribution"],
        "per_run": per_run,
        "per_group": per_group,
        "overall": overall,
        "policy_sha256": policy_sha,
        "policy_result": policy_result,
    }
    report_dir.mkdir(parents=True, exist_ok=True)
    (report_dir / "environment_evaluation.json").write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"rows": output["rows"], "policy": policy_result}, ensure_ascii=False))


if __name__ == "__main__":
    main()
