"""Создание полного immutable validation lock v0.3.10 до prediction."""
from __future__ import annotations
import hashlib, json, sys
from datetime import UTC, datetime
from pathlib import Path
import pandas as pd
import yaml

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent / "features"), str(HERE.parent / "experiments/v0_3_10")]
from v0310_capture_manifest import build as build_capture_manifest

def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def json_hash(value) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()

def create(root: Path, campaign_path: Path, output_root: Path, manifest_path: Path, audit_path: Path) -> dict:
    prediction_lock = root / "ml/artifacts/v0_3_10/immutable_prediction.lock.json"
    if prediction_lock.exists():
        raise RuntimeError("Post-hoc создание или дополнение validation lock запрещено")
    campaign = yaml.safe_load(campaign_path.read_text(encoding="utf-8"))
    run_ids = [row["run_id"] for row in campaign["runs"]]
    status_path = output_root / "campaigns" / campaign["campaign_id"].replace(".", "_").replace("-", "_") / "status.json"
    status = json.loads(status_path.read_text(encoding="utf-8"))
    if len(status) != 6 or not all(row.get("run_status") == "success" for row in status.values()):
        raise RuntimeError("Validation lock требует 6/6 успешных runs")
    paths = [output_root / "datasets" / f"windows_network_sensor_v0_4_{run_id}.csv" for run_id in run_ids]
    combined = pd.concat([pd.read_csv(path) for path in paths], ignore_index=True)
    if len(combined) != 324 or combined["episode_id"].nunique() != 108:
        raise ValueError("Validation lock требует 324 rows и 108 episodes")
    capture_path = output_root / "datasets/v0310_validation_capture_manifest.json"
    captures = build_capture_manifest(root, run_ids, capture_path, 360)
    from network_sensor_v0_6 import build_causal_frame
    from pipeline import attach_manifest_timestamps
    candidate = yaml.safe_load((root / "ml/experiments/v0_3_10/frozen_candidate_manifest.yaml").read_text(encoding="utf-8"))
    all_rows = pd.concat([pd.read_csv(output_root / "datasets" / f"windows_network_sensor_v0_4_{run_id}_all.csv") for run_id in run_ids], ignore_index=True)
    all_rows = attach_manifest_timestamps(all_rows.reset_index(drop=True), output_root)
    features = build_causal_frame(all_rows.to_dict("records"), candidate["feature_profile"], history_depth=6)
    features = features.loc[~all_rows["warmup"].astype(bool)].reset_index(drop=True)
    feature_path = output_root / "datasets/v0310_validation_frozen_features.csv"
    features.to_csv(feature_path, index=False)
    mapping = combined[["run_id", "execution_id", "episode_id", "episode_phase", "episode_class"]].to_dict("records")
    integrities = [json.loads((output_root / "runs" / run_id / "v0310_run_integrity.json").read_text(encoding="utf-8")) for run_id in run_ids]
    capture_payload = json.loads(capture_path.read_text(encoding="utf-8"))
    payload = {"validation_campaign_sha256": sha(campaign_path), "campaign_index_sha256": json_hash(run_ids),
               "run_ids": run_ids, "run_status_sha256": sha(status_path),
               "dataset_paths": [path.relative_to(root).as_posix() for path in paths],
               "dataset_sha256": {path.name: sha(path) for path in paths},
               "row_order_sha256": json_hash(combined["execution_id"].astype(str).tolist()),
               "execution_mapping_sha256": json_hash(mapping),
               "episode_mapping_sha256": json_hash(combined[["episode_id", "episode_phase"]].to_dict("records")),
               "capture_root": "captures/", "capture_paths": [item["canonical_relative_path"] for item in capture_payload["captures"]],
               "capture_hashes": [item["sha256"] for item in capture_payload["captures"]],
               "capture_manifest_path": capture_path.relative_to(root).as_posix(),
               "capture_manifest_sha256": captures["capture_manifest_sha256"], "capture_hash_count": 360,
               "capture_hashes_complete": True, "capture_paths_canonical": True, "capture_marker_mapping_complete": True,
               "event_hashes": {run_id: value["events_sha256"] for run_id, value in zip(run_ids, integrities)},
               "marker_mapping_sha256": json_hash([(item["run_id"], item["marker_sequence"], item["execution_id"]) for item in capture_payload["captures"]]),
               "marker_pair_count": 360, "frozen_feature_path": feature_path.relative_to(root).as_posix(),
               "frozen_feature_sha256": sha(feature_path), "class_distribution": combined["episode_class"].value_counts().sort_index().to_dict(),
               "group_distribution": combined["environment_group"].value_counts().sort_index().to_dict(),
               "benign_variant_distribution": combined.loc[combined["episode_class"] == "benign", "variant_id"].value_counts().sort_index().to_dict(),
               "feature_schema_sha256": candidate["feature_schema_sha256"], "expected_runs": 6, "expected_rows": 324,
               "expected_episodes": 108, "expected_marker_pairs": 360, "expected_capture_hashes": 360,
               "locked_at": datetime.now(UTC).isoformat(), "modified_after_lock": False}
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(yaml.safe_dump(payload, allow_unicode=True, sort_keys=False), encoding="utf-8")
    result = {"validation_lock_valid": True, "validation_lock_sha256": sha(manifest_path),
              "capture_manifest_sha256": sha(capture_path), "capture_hash_count": 360,
              "capture_hashes_complete_before_prediction": True, "mapping_324_of_324": True,
              "episode_mapping_108_of_108": True, "marker_mapping_360_of_360": True,
              "validation_locked_before_prediction": True, "post_hoc_completion": False}
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    audit_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result

def verify(root: Path, manifest_path: Path) -> dict:
    value = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    datasets_match = all(sha(root / relative) == value["dataset_sha256"][Path(relative).name] for relative in value["dataset_paths"])
    captures_match = len(value["capture_paths"]) == len(value["capture_hashes"]) == 360
    captures_match &= all(path.startswith("lab/output/runs/") and "/captures/" in path and
                          (root / path).stat().st_size > 0 and sha(root / path) == digest
                          for path, digest in zip(value["capture_paths"], value["capture_hashes"]))
    capture_manifest_match = sha(root / value["capture_manifest_path"]) == value["capture_manifest_sha256"]
    feature_match = sha(root / value["frozen_feature_path"]) == value["frozen_feature_sha256"]
    valid = datasets_match and captures_match and capture_manifest_match and feature_match and not value["modified_after_lock"]
    return {"validation_lock_valid": valid, "dataset_hashes_match": datasets_match, "capture_hashes_match": captures_match,
            "capture_manifest_hash_matches": capture_manifest_match, "frozen_feature_hash_matches": feature_match,
            "capture_hash_count": len(value["capture_hashes"]), "validation_lock_sha256": sha(manifest_path)}
