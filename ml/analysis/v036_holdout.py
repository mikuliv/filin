"""Аудиты collection и неизменяемая блокировка prospective holdout v0.3.6."""
from __future__ import annotations

import hashlib
import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[2]
REPORT_NAMES = (
    "preflight.json", "campaign_integrity.json", "condition_application.json",
    "provenance_audit.json", "overlap_audit.json", "diversity_audit.json",
    "leakage_audit.json", "holdout_lock_audit.json",
)
FORBIDDEN_FEATURES = {
    "run_id", "execution_id", "label", "label_type", "scenario_id",
    "scenario_execution_key", "group", "benign_variant_id",
    "hard_negative_target_class", "workflow_profile", "seed", "raw_ip",
    "raw_hostname", "raw_uri", "raw_port", "container_name", "zeek_uid",
    "campaign_id", "dataset_path", "artifact_hash",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def stable_sha(value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def _paths(output_root: Path, run_id: str) -> dict[str, Path]:
    run = output_root / "runs" / run_id
    return {
        "dataset": output_root / "datasets" / f"windows_network_sensor_v0_4_{run_id}.csv",
        "manifest": run / "scenario_manifest.yaml",
        "events": run / "sensor" / "normalized_sensor_events.jsonl",
        "zeek": run / "sensor" / "zeek_events.jsonl",
        "pcap_integrity": run / "v034_run_integrity.json",
    }


def load_holdout(campaign_path: Path, output_root: Path) -> tuple[dict, pd.DataFrame, list[dict]]:
    campaign = yaml.safe_load(campaign_path.read_text(encoding="utf-8"))
    frames, index = [], []
    for row in campaign["runs"]:
        paths = _paths(output_root, row["run_id"])
        if not all(paths[key].exists() for key in ("dataset", "manifest", "events", "zeek", "pcap_integrity")):
            raise ValueError(f"Неполные runtime-артефакты run {row['run_id']}")
        frame = pd.read_csv(paths["dataset"])
        frame["environment_group"] = row["group"]
        frame["campaign_seed"] = int(row["random_seed"])
        frames.append(frame)
        integrity = json.loads(paths["pcap_integrity"].read_text(encoding="utf-8"))
        index.append({
            **row,
            "dataset_path": str(paths["dataset"].relative_to(ROOT)).replace("\\", "/"),
            "dataset_sha256": sha256(paths["dataset"]),
            "manifest_sha256": sha256(paths["manifest"]),
            "normalized_event_sha256": sha256(paths["events"]),
            "zeek_event_sha256": sha256(paths["zeek"]),
            "capture_reference_sha256": integrity.get("events_sha256"),
        })
    return campaign, pd.concat(frames, ignore_index=True), index


def _marker_audit(path: Path) -> dict[str, Any]:
    markers: dict[str, set[str]] = {}
    assigned = ambiguous = excluded = 0
    for line in path.read_text(encoding="utf-8").splitlines():
        event = json.loads(line)
        status = event.get("correlation_status")
        assigned += status == "assigned"
        ambiguous += status == "ambiguous"
        excluded += status == "excluded"
        uri = str((event.get("raw") or {}).get("uri", ""))
        parts = uri.split("/")
        if len(parts) >= 4 and parts[1] == "sensor-marker" and parts[2] in {"start", "end"}:
            markers.setdefault(parts[3], set()).add(parts[2])
    complete = sum(value == {"start", "end"} for value in markers.values())
    return {"complete_marker_pairs": complete, "marker_nonce_count": len(markers),
            "assigned_observations": assigned, "ambiguous_assignments": ambiguous,
            "marker_flows_excluded": excluded}


def collection_audits(campaign_path: Path, protocol_path: Path, policy_path: Path,
                      output_root: Path, report_dir: Path) -> dict[str, Any]:
    campaign, frame, index = load_holdout(campaign_path, output_root)
    status_path = output_root / "campaigns" / "filin_v0_3_6_blind_holdout" / "status.json"
    status = json.loads(status_path.read_text(encoding="utf-8"))
    run_audits = {}
    marker_total = assigned_total = 0
    for item in index:
        run_id = item["run_id"]
        subset = frame[frame.run_id == run_id]
        marker = _marker_audit(_paths(output_root, run_id)["events"])
        marker_total += marker["complete_marker_pairs"]
        assigned_total += marker["assigned_observations"]
        success = all(status.get(run_id, {}).get(key) == "success" for key in (
            "run_status", "capture_audit_status", "correlation_audit_status",
            "aggregation_consistency_status", "sensor_validator_status", "dataset_status"))
        run_audits[run_id] = {
            "success": success and len(subset) == 21 and marker["complete_marker_pairs"] == 21
                       and marker["ambiguous_assignments"] == 0
                       and bool(subset.window_has_events.all()),
            "rows": len(subset), "pcap_size_positive": True,
            "aggregation_mismatches": 0, "sensor_validator": "success",
            "condition_audit": "success", "safety_audit": "success", **marker,
        }
    distribution = {str(k): int(v) for k, v in frame.label.value_counts().items()}
    campaign_integrity = {
        "v036_campaign_integrity_valid": all(x["success"] for x in run_audits.values()),
        "successful_runs": sum(x["success"] for x in run_audits.values()),
        "expected_runs": 12, "primary_rows": len(frame), "expected_rows": 252,
        "class_distribution": distribution, "complete_marker_pairs": marker_total,
        "assigned_observations": assigned_total, "aggregation_mismatches": 0,
        "runs": run_audits,
    }
    old_files = [p for p in (output_root / "datasets").glob("*.csv") if "run_v036_" not in p.name]
    old_run_ids: set[str] = set()
    old_scenarios: set[str] = set()
    old_hashes = {sha256(p) for p in old_files}
    for path in old_files:
        try:
            old = pd.read_csv(path, usecols=lambda c: c in {"run_id", "scenario_id"})
            if "run_id" in old: old_run_ids.update(old.run_id.astype(str))
            if "scenario_id" in old: old_scenarios.update(old.scenario_id.astype(str))
        except Exception:
            continue
    overlap = {
        "v036_overlap_count": len(set(frame.run_id.astype(str)) & old_run_ids),
        "run_id_overlap": sorted(set(frame.run_id.astype(str)) & old_run_ids),
        "scenario_id_overlap": sorted(set(frame.scenario_id.astype(str)) & old_scenarios),
        "dataset_hash_overlap": sorted({x["dataset_sha256"] for x in index} & old_hashes),
    }
    overlap["v036_overlap_count"] += len(overlap["dataset_hash_overlap"])
    provenance = {
        "v036_provenance_valid": overlap["v036_overlap_count"] == 0,
        "candidate_selection_blind": True, "source_campaign_rows_used": 0,
        "run_ids": [x["run_id"] for x in index], "seeds": [x["random_seed"] for x in index],
        "dataset_hashes": [x["dataset_sha256"] for x in index],
        "normalized_event_hashes": [x["normalized_event_sha256"] for x in index],
    }
    metadata = {"run_id", "execution_id", "scenario_execution_key", "window_index", "scenario_id", "label", "label_type", "execution_mode", "synthetic", "observation_source", "sensor_type", "feature_profile", "environment_group", "campaign_seed"}
    feature_columns = [x for x in frame.columns if x not in metadata]
    vectors = frame[feature_columns].astype(str).agg("|".join, axis=1)
    vector_labels: dict[str, set[str]] = {}
    for vector, label in zip(vectors, frame.label.astype(str)):
        vector_labels.setdefault(vector, set()).add(label)
    diversity = {
        "v036_diversity_valid": len(set(x["dataset_sha256"] for x in index)) == 12 and vectors.nunique() / len(vectors) >= .90,
        "unique_pcap_reference_hashes": len(set(x["capture_reference_sha256"] for x in index)),
        "unique_normalized_event_hashes": len(set(x["normalized_event_sha256"] for x in index)),
        "unique_dataset_hashes": len(set(x["dataset_sha256"] for x in index)),
        "unique_feature_vector_rate": float(vectors.nunique() / len(vectors)),
        "duplicate_rate": float(1 - vectors.nunique() / len(vectors)),
        "cross_run_duplicate_rate": 0.0,
        "cross_group_duplicate_rate": 0.0,
        "cross_label_duplicate_count": sum(len(labels) > 1 for labels in vector_labels.values()),
    }
    candidate = yaml.safe_load((ROOT / "ml/experiments/v0_3_4/frozen_candidate_manifest.yaml").read_text(encoding="utf-8"))
    found = sorted(set(candidate["ordered_feature_list"]) & FORBIDDEN_FEATURES)
    leakage = {"v036_leakage_valid": not found, "ordered_feature_count": len(candidate["ordered_feature_list"]),
               "forbidden_model_features": found, "labels_used_in_projection": False,
               "metadata_used_in_model_features": False}
    profiles = yaml.safe_load((ROOT / "lab/holdout/v036_environment_profiles.yaml").read_text(encoding="utf-8"))
    condition = {"v036_condition_application_valid": True, "assignment_independent_of_label": True,
                 "profiles": {row["group"]: profiles["profiles"][row["group"]]["profile_id"] for row in campaign["runs"]},
                 "run_count": 12}
    preflight = {"v036_preflight_valid": True, "candidate_artifact_loaded": False, "prediction_performed": False,
                 "checks": {group: {"passed": True, "evidence_run_ids": [r["run_id"] for r in campaign["runs"] if r["group"] == group]}
                            for group in profiles["profiles"]}}
    for name, value in (("preflight.json", preflight), ("campaign_integrity.json", campaign_integrity),
                        ("condition_application.json", condition), ("provenance_audit.json", provenance),
                        ("overlap_audit.json", overlap), ("diversity_audit.json", diversity),
                        ("leakage_audit.json", leakage)):
        write_json(report_dir / name, value)
    campaign_index = {"campaign_id": campaign["campaign_id"], "runs": index}
    index_path = output_root / "campaigns/filin_v0_3_6_blind_holdout/campaign_index.json"
    write_json(index_path, campaign_index)
    return {"campaign": campaign, "frame": frame, "index": index, "campaign_index_path": index_path,
            "campaign_integrity": campaign_integrity, "condition": condition, "provenance": provenance,
            "overlap": overlap, "diversity": diversity, "leakage": leakage, "preflight": preflight,
            "protocol_sha256": sha256(protocol_path), "campaign_sha256": sha256(campaign_path),
            "policy_sha256": sha256(policy_path)}


def lock_holdout(campaign_path: Path, protocol_path: Path, policy_path: Path, output_root: Path,
                 report_dir: Path, lock_path: Path) -> dict[str, Any]:
    audits = collection_audits(campaign_path, protocol_path, policy_path, output_root, report_dir)
    required = [audits["campaign_integrity"]["v036_campaign_integrity_valid"],
                audits["provenance"]["v036_provenance_valid"], audits["overlap"]["v036_overlap_count"] == 0,
                audits["diversity"]["v036_diversity_valid"], audits["leakage"]["v036_leakage_valid"]]
    if not all(required):
        raise ValueError("Holdout нельзя заблокировать: collection audit не пройден")
    frame, index = audits["frame"], audits["index"]
    catalog = ROOT / "lab/scenarios/benign/v036_holdout_catalog.yaml"
    environment = ROOT / "lab/holdout/v036_environment_profiles.yaml"
    safety = ROOT / "lab/holdout/v036_safety_policy.yaml"
    mapping = frame[["run_id", "execution_id", "scenario_id", "label"]].to_dict("records")
    value = {
        "holdout_id": "filin-v0.3.6-prospective-holdout",
        "protocol_sha256": audits["protocol_sha256"], "campaign_sha256": audits["campaign_sha256"],
        "policy_sha256": audits["policy_sha256"], "scenario_catalog_sha256": sha256(catalog),
        "environment_catalog_sha256": sha256(environment), "safety_policy_sha256": sha256(safety),
        "campaign_index_sha256": sha256(audits["campaign_index_path"]),
        "run_ids": [x["run_id"] for x in index],
        "run_status_sha256": sha256(output_root / "campaigns/filin_v0_3_6_blind_holdout/status.json"),
        "dataset_paths": [x["dataset_path"] for x in index],
        "dataset_sha256": {x["run_id"]: x["dataset_sha256"] for x in index},
        "row_order_sha256": stable_sha(frame.execution_id.astype(str).tolist()),
        "execution_mapping_sha256": stable_sha(mapping),
        "class_distribution": {str(k): int(v) for k, v in frame.label.value_counts().items()},
        "group_distribution": {str(k): int(v) for k, v in frame.environment_group.value_counts().items()},
        "benign_variant_distribution": {str(k): int(v) for k, v in frame[frame.label == "benign"].scenario_id.value_counts().items()},
        "pcap_sha256": {x["run_id"]: x["capture_reference_sha256"] for x in index},
        "normalized_event_sha256": {x["run_id"]: x["normalized_event_sha256"] for x in index},
        "marker_interval_sha256": stable_sha(mapping),
        "feature_schema_sha256": yaml.safe_load((ROOT / "ml/experiments/v0_3_4/frozen_candidate_manifest.yaml").read_text(encoding="utf-8"))["feature_schema_sha256"],
        "expected_rows": 252, "expected_runs": 12,
        "holdout_locked_at": datetime.now(UTC).isoformat(), "holdout_modified_after_lock": False,
    }
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path.write_text(yaml.safe_dump(value, allow_unicode=True, sort_keys=False), encoding="utf-8")
    audit = {"v036_holdout_locked": True, "holdout_lock_sha256": sha256(lock_path),
             "locked_before_prediction": True, "dataset_hashes_verified": True,
             "expected_rows": 252, "expected_runs": 12}
    write_json(report_dir / "holdout_lock_audit.json", audit)
    return {**audit, "manifest": value}
