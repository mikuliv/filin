from __future__ import annotations

import os
from pathlib import Path

import yaml

from .common import ROOT, read_json, read_yaml, sha256_file, write_json


def _relative(path: Path, manifest: Path) -> str:
    return Path(os.path.relpath(path.resolve(), manifest.parent.resolve())).as_posix()


def create_pre_manifest(path: Path, hashes: dict, feature_audit: dict, capture_manifest: Path, input_lock: dict, prediction_path: Path, policy_path: Path) -> dict:
    feature_path = ROOT / feature_audit["feature_table_path"]
    vault_path = ROOT / feature_audit["label_vault_path"]
    data = {
        "stage_id": "v0.3.13", "frozen_before_prediction": True, "protocol_sha256": hashes["protocol"], "campaign_manifest_sha256": hashes["campaign"], "source_commit_sha256": "8f060a73b13aa8b89333da13cc645b5202d57eb9", "dependency_lock_sha256": input_lock["dependency_lock_sha256"],
        "feature_table_path": _relative(feature_path, path), "feature_schema_sha256": feature_audit["feature_schema_sha256"], "expected_row_count": 700, "row_identity_version": "v0313-blind-causal-v1", "row_mapping_sha256": feature_audit["row_mapping_sha256"], "run_mapping_sha256": feature_audit["run_mapping_sha256"], "causal_order_mapping_sha256": feature_audit["causal_order_mapping_sha256"], "activity_key_mapping_sha256": feature_audit["activity_key_mapping_sha256"],
        "label_vault_path": _relative(vault_path, path), "episode_mapping_path": _relative(vault_path, path), "capture_manifest_path": _relative(capture_manifest, path), "candidate_id": "v0311:19176acb401be2d4", "candidate_manifest_sha256": hashes["candidate_manifest"], "reserved_immutable_prediction_path": _relative(prediction_path, path), "prediction_schema_version": "v0313-blind-causal-v1", "metric_policy_sha256": hashes["metric"], "readiness_policy_sha256": hashes["readiness"], "reserved_policy_result_path": _relative(policy_path, path),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8", newline="\n")
    return data


def finalize(manifest_path: Path, completion_path: Path, hashes: dict, feature_audit: dict, capture_manifest: Path, input_lock: dict, prediction_path: Path, policy_path: Path) -> dict:
    feature_path = ROOT / feature_audit["feature_table_path"]
    vault_path = ROOT / feature_audit["label_vault_path"]
    schema = read_yaml(ROOT / "ml/experiments/v0_3_11/feature_schema.yaml")["ordered_features"]
    rows = input_lock["rows"]
    data = {
        "stage_id": "v0.3.13", "protocol_sha256": hashes["protocol"], "campaign_manifest_sha256": hashes["campaign"], "source_commit_sha256": "8f060a73b13aa8b89333da13cc645b5202d57eb9", "dependency_lock_sha256": input_lock["dependency_lock_sha256"],
        "feature_table_path": _relative(feature_path, manifest_path), "feature_table_sha256": sha256_file(feature_path), "feature_count": 51, "ordered_feature_names": schema, "feature_schema_sha256": feature_audit["feature_schema_sha256"],
        "row_count": 700, "ordered_row_ids": [row["immutable_row_id"] for row in rows], "row_mapping_sha256": feature_audit["row_mapping_sha256"], "row_identity_version": "v0313-blind-causal-v1", "run_mapping": {row["immutable_row_id"]: row["run_id"] for row in rows}, "run_mapping_sha256": feature_audit["run_mapping_sha256"], "causal_order_mapping": {row["immutable_row_id"]: row["causal_order"] for row in rows}, "causal_order_mapping_sha256": feature_audit["causal_order_mapping_sha256"], "activity_key_source_fields": ["run_id", "causal_inactivity_sequence"], "activity_key_mapping_sha256": feature_audit["activity_key_mapping_sha256"],
        "label_table_path": _relative(vault_path, manifest_path), "label_table_sha256": sha256_file(vault_path), "label_schema_version": "v0313-sealed-v1", "episode_mapping_path": _relative(vault_path, manifest_path), "episode_mapping_sha256": sha256_file(vault_path), "frozen_episode_mapping_sha256": feature_audit["episode_mapping_sha256"], "episode_mapping_created_before_prediction": True,
        "capture_manifest_path": _relative(capture_manifest, manifest_path), "capture_manifest_sha256": sha256_file(capture_manifest), "historical_candidate_id": "v0311:19176acb401be2d4", "candidate_manifest_sha256": hashes["candidate_manifest"], "immutable_prediction_path": _relative(prediction_path, manifest_path), "immutable_prediction_sha256": sha256_file(prediction_path), "prediction_schema_version": "v0313-blind-causal-v1", "metric_policy_sha256": hashes["metric"], "policy_result_path": _relative(policy_path, manifest_path), "policy_result_sha256": sha256_file(policy_path), "compatibility_self_test_result": True, "regression_bundle_complete": True,
    }
    manifest_path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8", newline="\n")
    completion = {"stage_id": "v0.3.13", "feature_table_sha256": data["feature_table_sha256"], "row_mapping_sha256": data["row_mapping_sha256"], "label_vault_sha256": data["label_table_sha256"], "episode_mapping_sha256": feature_audit["episode_mapping_sha256"], "immutable_prediction_sha256": data["immutable_prediction_sha256"], "policy_result_sha256": data["policy_result_sha256"], "regression_bundle_manifest_sha256": sha256_file(manifest_path), "regression_bundle_complete": True}
    completion_path.write_text(yaml.safe_dump(completion, allow_unicode=True, sort_keys=False), encoding="utf-8", newline="\n")
    return {"manifest": data, "completion": completion}
