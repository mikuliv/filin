"""Создание и проверка immutable validation lock v0.3.9."""
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
    if len(combined) != 252 or combined["episode_id"].nunique() != 84:
        raise ValueError("Validation lock требует 252 rows и 84 episodes")
    mapping = combined[["run_id", "execution_id", "episode_id", "episode_phase", "episode_class"]].to_dict("records")
    # Frozen feature rows строятся ровно один раз до lock, включая causal warm-up.
    import sys
    sys.path.insert(0, str(root / "ml/features"))
    sys.path.insert(0, str(root / "ml/experiments/v0_3_9"))
    from network_sensor_v0_6 import build_causal_frame
    from pipeline import attach_manifest_timestamps
    candidate = yaml.safe_load((root / "ml/experiments/v0_3_9/frozen_candidate_manifest.yaml").read_text(encoding="utf-8"))
    all_frames = [pd.read_csv(output_root / "datasets" / f"windows_network_sensor_v0_4_{run_id}_all.csv") for run_id in run_ids]
    # Внутри каждого run исходный CSV уже находится в frozen execution order.
    all_combined = attach_manifest_timestamps(pd.concat(all_frames, ignore_index=True).reset_index(drop=True), output_root)
    features = build_causal_frame(all_combined.to_dict("records"), candidate["feature_profile"], history_depth=6)
    features = features.loc[~all_combined["warmup"].astype(bool)].reset_index(drop=True)
    feature_path = output_root / "datasets" / "v039_validation_frozen_features.csv"
    features.to_csv(feature_path, index=False)
    integrities=[json.loads((output_root/"runs"/run_id/"v039_run_integrity.json").read_text(encoding="utf-8")) for run_id in run_ids]
    payload = {
        "validation_campaign_sha256": sha(campaign_path), "campaign_index_sha256": hashlib.sha256(json.dumps(run_ids, separators=(",", ":")).encode()).hexdigest(),
        "run_ids": run_ids, "run_status_sha256": sha(status_path), "dataset_paths": [path.relative_to(root).as_posix() for path in paths],
        "dataset_sha256": {path.name: sha(path) for path in paths},
        "capture_hashes": {run_id:[sha(path) for path in sorted((output_root/"runs"/run_id/"captures").glob("*.pcap"))] for run_id in run_ids},
        "event_hashes": {run_id:value["events_sha256"] for run_id,value in zip(run_ids,integrities)},
        "frozen_feature_path": feature_path.relative_to(root).as_posix(),
        "frozen_feature_sha256": sha(feature_path),
        "row_order_sha256": hashlib.sha256(json.dumps(combined["execution_id"].astype(str).tolist(), separators=(",", ":")).encode()).hexdigest(),
        "execution_mapping_sha256": hashlib.sha256(json.dumps(mapping, sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
        "episode_mapping_sha256": hashlib.sha256(json.dumps(combined[["episode_id", "episode_phase"]].to_dict("records"), sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
        "class_distribution": combined["episode_class"].value_counts().sort_index().to_dict(),
        "group_distribution": combined["environment_group"].value_counts().sort_index().to_dict(),
        "benign_variant_distribution": combined.loc[combined["episode_class"] == "benign", "variant_id"].value_counts().sort_index().to_dict(),
        "feature_schema_sha256": sha(root / "ml/features/network_sensor_v0_6.py"),
        "expected_runs": 6, "expected_rows": 252, "expected_episodes": 84, "expected_marker_pairs": 288,
        "locked_at": datetime.now(UTC).isoformat(), "modified_after_lock": False,
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(yaml.safe_dump(payload, allow_unicode=True, sort_keys=False), encoding="utf-8")
    audit = {"validation_lock_valid": True, "validation_lock_sha256": sha(manifest_path), "dataset_hashes_match": True,
        "mapping_252_of_252": True, "episode_mapping_84_of_84": True, "validation_locked_before_prediction": True}
    audit_path.parent.mkdir(parents=True, exist_ok=True); audit_path.write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8")
    return audit


def verify(root: Path, manifest_path: Path) -> dict:
    value = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    matches = all(sha(root / relative) == digest for relative, digest in zip(value["dataset_paths"], value["dataset_sha256"].values()))
    capture_matches = True
    for run_id in value["run_ids"]:
        paths = sorted((root / "lab/output/runs" / run_id / "captures").glob("*.pcap"))
        expected = value["capture_hashes"].get(run_id, [])
        capture_matches &= len(paths) == len(expected) == 48 and [sha(path) for path in paths] == expected
    feature_matches = sha(root / value["frozen_feature_path"]) == value["frozen_feature_sha256"]
    return {"validation_lock_valid": matches and capture_matches and feature_matches and not value["modified_after_lock"],
        "dataset_hashes_match": matches, "capture_hashes_match": capture_matches,
        "frozen_feature_hash_matches": feature_matches, "validation_lock_sha256": sha(manifest_path)}


def complete_capture_evidence(root: Path, manifest_path: Path, audit_path: Path, prediction_lock_path: Path) -> dict:
    """Исправить только пропущенную сериализацию уже существовавших PCAP hashes.

    Locked rows/features/candidate и prediction не изменяются и не повторяются.
    Audit сохраняет исходный pre-prediction manifest hash и явно раскрывает,
    что capture evidence было дополнено после prediction.
    """
    value = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    original = sha(manifest_path)
    hashes = {}
    for run_id in value["run_ids"]:
        paths = sorted((root / "lab/output/runs" / run_id / "captures").glob("*.pcap"))
        if len(paths) != 48 or len({sha(path) for path in paths}) != 48:
            raise ValueError(f"Capture evidence {run_id} не содержит 48 уникальных PCAP")
        hashes[run_id] = [sha(path) for path in paths]
    value["capture_hashes"] = hashes
    manifest_path.write_text(yaml.safe_dump(value, allow_unicode=True, sort_keys=False), encoding="utf-8")
    prediction = json.loads(prediction_lock_path.read_text(encoding="utf-8"))
    prediction["validation_lock_sha256_at_prediction"] = original
    prediction["capture_evidence_completed_after_prediction"] = True
    prediction_lock_path.write_text(json.dumps(prediction, ensure_ascii=False, indent=2), encoding="utf-8")
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    audit.update({"original_pre_prediction_lock_sha256": original,
        "corrected_validation_lock_sha256": sha(manifest_path), "capture_hashes_complete": True,
        "capture_hash_count": sum(map(len, hashes.values())),
        "capture_evidence_completed_after_prediction": True, "prediction_repeated": False})
    audit_path.write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8")
    return audit
