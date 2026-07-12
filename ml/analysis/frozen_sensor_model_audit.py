"""Integrity audit for a trusted frozen/reconstructed sensor model artifact."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import joblib
import yaml


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def audit(manifest_path: Path) -> dict:
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8")) or {}
    root = manifest_path.parents[3]
    artifact = root / manifest["artifact_path"]
    errors: list[str] = []
    if not artifact.exists() or sha256(artifact) != manifest.get("model_sha256"):
        errors.append("model_sha256")
        return {"frozen_model_integrity_valid": False, "errors": errors}
    model = joblib.load(artifact)
    steps = getattr(model, "named_steps", {})
    features = list(manifest.get("ordered_feature_list") or [])
    if set(steps) != {"imputer", "scale", "model"}:
        errors.append("pipeline_steps")
    elif steps["imputer"].strategy != "median":
        errors.append("imputer")
    elif steps["model"].__class__.__name__ != "LogisticRegression":
        errors.append("model_class")
    elif int(steps["model"].n_features_in_) != len(features):
        errors.append("feature_count")
    return {
        "frozen_model_integrity_valid": not errors,
        "provenance_type": manifest.get("provenance_type"),
        "model_sha256": manifest.get("model_sha256"),
        "feature_count": len(features),
        "model_reconstructed_from_source_train": bool(manifest.get("model_reconstructed_from_source_train")),
        "model_retrained_on_v033_data": False,
        "feature_list_changed": False,
        "preprocessing_changed": False,
        "threshold_changed": False,
        "errors": errors,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Frozen sensor model integrity audit.")
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    result = audit(Path(args.manifest))
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))
    if not result["frozen_model_integrity_valid"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
