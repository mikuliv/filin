from __future__ import annotations

from pathlib import Path

from .common import ROOT, read_json, sha256_file, sha256_json, write_json


def create(config_hashes: dict, capture_manifest: Path, feature_audit: dict, output: Path, prediction_code: Path) -> dict:
    rows = read_json(ROOT / feature_audit["row_mapping_path"])["rows"]
    payload = {
        "protocol_sha256": config_hashes["protocol"], "campaign_manifest_sha256": config_hashes["campaign"], "scenario_manifest_sha256": config_hashes["scenario"], "candidate_artifact_sha256": config_hashes["candidate_artifact"], "candidate_manifest_sha256": config_hashes["candidate_manifest"],
        "capture_manifest_sha256": sha256_file(capture_manifest), "feature_table_sha256": feature_audit["feature_table_sha256"], "feature_schema_sha256": feature_audit["feature_schema_sha256"], "canonical_feature_matrix_sha256": feature_audit["feature_table_sha256"],
        "ordered_row_mapping_sha256": feature_audit["row_mapping_sha256"], "run_mapping_sha256": feature_audit["run_mapping_sha256"], "causal_order_mapping_sha256": feature_audit["causal_order_mapping_sha256"], "activity_key_mapping_sha256": feature_audit["activity_key_mapping_sha256"], "episode_mapping_structure_sha256": feature_audit["episode_mapping_sha256"],
        "dependency_lock_sha256": sha256_file(ROOT / "ml/requirements.txt"), "source_commit_sha256": "8f060a73b13aa8b89333da13cc645b5202d57eb9", "prediction_code_sha256": sha256_file(prediction_code), "scored_row_count": 700, "episode_count": 200, "marker_count": 760, "capture_count": 760, "feature_count": 51, "benchmark_id": "v0313_environmental_blind_holdout", "rows": rows,
    }
    payload["input_lock_sha256"] = sha256_json({key: value for key, value in payload.items() if key != "rows"})
    write_json(output, payload)
    return payload
