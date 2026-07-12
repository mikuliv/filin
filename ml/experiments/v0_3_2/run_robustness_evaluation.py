"""External v0.3.2 evaluation: load an audited artifact and predict only."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import joblib
import pandas as pd
import yaml
from sklearn.metrics import balanced_accuracy_score, f1_score, recall_score


ATTACKS = ["port_scan", "auth_failures", "web_probe", "low_rate_dos", "beacon_simulation"]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def evaluate(model, frame: pd.DataFrame, features: list[str]) -> dict[str, float]:
    prediction = model.predict(frame.loc[:, features])
    return {
        "macro_f1": float(f1_score(frame.label, prediction, average="macro", zero_division=0)),
        "balanced_accuracy": float(balanced_accuracy_score(frame.label, prediction)),
        "attack_macro_recall": float(recall_score(frame.label, prediction, labels=ATTACKS, average="macro", zero_division=0)),
    }


def run(manifest_path: Path, datasets: list[Path], output_dir: Path) -> dict:
    """Load an existing reconstructed artifact; this function deliberately has no fit."""
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    artifact = (manifest_path.parents[3] / manifest["artifact_path"]).resolve()
    expected = manifest["model_sha256"]
    if sha256(artifact) != expected:
        raise ValueError("Frozen artifact SHA-256 mismatch")
    model = joblib.load(artifact)
    features = list(manifest["ordered_feature_list"])
    robust = pd.concat([pd.read_csv(path) for path in datasets], ignore_index=True)
    if any(list(frame.columns[frame.columns.isin(features)]) != features for frame in [robust]):
        raise ValueError("Robustness feature order differs from frozen artifact")
    per_run = {run_id: evaluate(model, frame, features) for run_id, frame in robust.groupby("run_id", sort=True)}
    result = {"frozen_model_class": type(model.named_steps["model"]).__name__, "robustness_rows": len(robust), "per_run": per_run, "pooled": evaluate(model, robust, features), "model_retrained_on_robustness_data": False, "evaluation_mode": "load_transform_predict"}
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "robustness_evaluation.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="External evaluation of a deterministically reconstructed v0.3.1 baseline.")
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--datasets", nargs="+", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()
    print(json.dumps(run(Path(args.manifest), [Path(path) for path in args.datasets], Path(args.output_dir)), ensure_ascii=False))


if __name__ == "__main__":
    main()
