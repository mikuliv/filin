"""Freeze v0.3.4 candidate before the validation loader is permitted."""
from __future__ import annotations
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
import joblib
import yaml

from run_v0_3_4_model_selection import MODELS, build_pipeline
from v034_dataset_loader import load_v034_dataset, sha256
from v034_data_access import load_policy, policy_sha256


def freeze(selection_path: Path, datasets: list[Path], access_path: Path, selection_policy_path: Path, campaign_path: Path, artifact_dir: Path, manifest_path: Path) -> dict[str, Any]:
    selection = json.loads(selection_path.read_text(encoding="utf-8")); candidate = selection.get("candidate")
    if not selection.get("v034_cv_passed") or not candidate:
        return {"candidate_frozen": False, "reason": "cv_policy_failed"}
    access = load_policy(access_path); policy = yaml.safe_load(selection_policy_path.read_text(encoding="utf-8"))
    spec = policy["model_selection_policy"]["candidates"][candidate["model"]]
    X, y, groups, _ = load_v034_dataset(datasets, access, candidate["profile"])
    pipeline = build_pipeline(spec, candidate["parameters"]); pipeline.fit(X, y)
    artifact_dir.mkdir(parents=True, exist_ok=True); artifact = artifact_dir / "frozen_candidate.joblib"; joblib.dump(pipeline, artifact)
    feature_schema = json.dumps(list(X.columns), ensure_ascii=False, separators=(",", ":")).encode()
    manifest = {
        "candidate_id": candidate["candidate_id"], "feature_profile": candidate["profile"], "ordered_feature_list": list(X.columns),
        "feature_schema_sha256": hashlib.sha256(feature_schema).hexdigest(), "training_campaign_sha256": sha256(campaign_path),
        "training_dataset_sha256": hashlib.sha256("".join(sha256(path) for path in datasets).encode()).hexdigest(),
        "data_access_policy_sha256": policy_sha256(access_path), "model_selection_policy_sha256": sha256(selection_policy_path),
        "model_class": spec["class"], "model_parameters": {**spec.get("parameters", {}), **candidate["parameters"]},
        "preprocessing": spec.get("preprocessing", []), "classes": sorted(y.unique()), "artifact_sha256": sha256(artifact),
        "source_train_run_ids": sorted(groups.unique()), "cv_metrics": candidate["metrics"],
        "candidate_frozen_at": datetime.now(UTC).isoformat(), "prohibit_refit_on_validation": True, "prohibit_refit_on_v033": True,
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True); manifest_path.write_text(yaml.safe_dump(manifest, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return {"candidate_frozen": True, "artifact": str(artifact), "manifest_sha256": sha256(manifest_path), **manifest}
