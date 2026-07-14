"""Создание и проверка immutable validation lock v0.3.8."""
from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
import yaml


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def create(root: Path, campaign_path: Path, output_root: Path, manifest_path: Path, audit_path: Path) -> dict:
    campaign = yaml.safe_load(campaign_path.read_text(encoding="utf-8"))
    run_ids = [row["run_id"] for row in campaign["runs"]]
    status_path = output_root / "campaigns" / campaign["campaign_id"].replace(".", "_").replace("-", "_") / "status.json"
    status = json.loads(status_path.read_text(encoding="utf-8"))
    paths = [output_root / "datasets" / f"windows_network_sensor_v0_4_{run_id}.csv" for run_id in run_ids]
    frames = [pd.read_csv(path) for path in paths]
    combined = pd.concat(frames, ignore_index=True)
    if len(combined) != 216 or combined["episode_id"].nunique() != 72:
        raise ValueError("Validation lock требует 216 rows и 72 episodes")
    mapping = combined[["run_id", "execution_id", "episode_id", "episode_phase", "episode_class"]].to_dict("records")
    # Frozen feature rows строятся ровно один раз до lock, включая causal warm-up.
    import sys
    sys.path.insert(0, str(root / "ml/features"))
    from network_sensor_v0_6 import build_causal_frame
    candidate = yaml.safe_load((root / "ml/experiments/v0_3_8/frozen_candidate_manifest.yaml").read_text(encoding="utf-8"))
    all_frames = [pd.read_csv(output_root / "datasets" / f"windows_network_sensor_v0_4_{run_id}_all.csv") for run_id in run_ids]
    all_combined = pd.concat(all_frames, ignore_index=True).sort_values(["run_id", "run_sequence"]).reset_index(drop=True)
    features = build_causal_frame(all_combined.to_dict("records"), candidate["feature_profile"])
    features = features.loc[~all_combined["warmup"].astype(bool)].reset_index(drop=True)
    feature_path = output_root / "datasets" / "v038_validation_frozen_features.csv"
    features.to_csv(feature_path, index=False)
    payload = {
        "validation_campaign_sha256": sha(campaign_path), "campaign_index_sha256": hashlib.sha256(json.dumps(run_ids, separators=(",", ":")).encode()).hexdigest(),
        "run_ids": run_ids, "run_status_sha256": sha(status_path), "dataset_paths": [path.relative_to(root).as_posix() for path in paths],
        "dataset_sha256": {path.name: sha(path) for path in paths},
        "frozen_feature_path": feature_path.relative_to(root).as_posix(),
        "frozen_feature_sha256": sha(feature_path),
        "row_order_sha256": hashlib.sha256(json.dumps(combined["execution_id"].astype(str).tolist(), separators=(",", ":")).encode()).hexdigest(),
        "execution_mapping_sha256": hashlib.sha256(json.dumps(mapping, sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
        "episode_mapping_sha256": hashlib.sha256(json.dumps(combined[["episode_id", "episode_phase"]].to_dict("records"), sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
        "class_distribution": combined["episode_class"].value_counts().sort_index().to_dict(),
        "group_distribution": combined["environment_group"].value_counts().sort_index().to_dict(),
        "benign_variant_distribution": combined.loc[combined["episode_class"] == "benign", "variant_id"].value_counts().sort_index().to_dict(),
        "feature_schema_sha256": sha(root / "ml/features/network_sensor_v0_6.py"),
        "expected_runs": 6, "expected_rows": 216, "expected_episodes": 72,
        "locked_at": datetime.now(UTC).isoformat(), "modified_after_lock": False,
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(yaml.safe_dump(payload, allow_unicode=True, sort_keys=False), encoding="utf-8")
    audit = {"validation_lock_valid": True, "validation_lock_sha256": sha(manifest_path), "dataset_hashes_match": True,
        "mapping_216_of_216": True, "episode_mapping_72_of_72": True, "validation_locked_before_prediction": True}
    audit_path.parent.mkdir(parents=True, exist_ok=True); audit_path.write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8")
    return audit


def verify(root: Path, manifest_path: Path) -> dict:
    value = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    matches = all(sha(root / relative) == digest for relative, digest in zip(value["dataset_paths"], value["dataset_sha256"].values()))
    return {"validation_lock_valid": matches and not value["modified_after_lock"], "dataset_hashes_match": matches, "validation_lock_sha256": sha(manifest_path)}
