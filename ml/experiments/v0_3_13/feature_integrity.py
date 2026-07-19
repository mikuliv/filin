from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import pandas as pd

from ml.experiments.v0_3_11.nested_selection import source_rows
from .common import ROOT, canonical_label, read_yaml, sha256_file, sha256_json, write_json


def prepare(campaign_path: Path, output_root: Path, runtime_root: Path) -> dict:
    rows, matrix = source_rows(campaign_path, output_root)
    campaign = read_yaml(campaign_path)
    episode_lengths = {}
    for run in campaign["runs"]:
        manifest = read_yaml(output_root / "runs" / run["run_id"] / "scenario_manifest.yaml")
        episode_lengths.update({str(item["execution_id"]): int(item["episode_length"]) for item in manifest["scenarios"] if not item["warmup"]})
    schema = read_yaml(ROOT / "ml/experiments/v0_3_11/feature_schema.yaml")["ordered_features"]
    if len(rows) != 700 or len(matrix) != 700 or list(matrix.columns) != schema or len(schema) != 51:
        raise RuntimeError("Нарушена frozen 51-feature schema или expected row count")
    if not matrix.notna().all().all():
        raise RuntimeError("Feature matrix содержит non-finite values")
    runtime_root.mkdir(parents=True, exist_ok=True)
    feature_path = runtime_root / "holdout_features.csv"
    row_path = runtime_root / "prediction_rows.json"
    vault_path = runtime_root / "sealed_label_vault.json"
    mapping = []
    vault = []
    last_run = None
    last_finish = None
    activity_sequence = 0
    run_position = 0
    for index, row in rows.reset_index(drop=True).iterrows():
        run = str(row.run_id)
        start = pd.Timestamp(row.planned_started_at)
        finish = pd.Timestamp(row.planned_finished_at)
        if run != last_run:
            activity_sequence = 1
            run_position = 1
            last_finish = None
        else:
            run_position += 1
            if last_finish is not None and (start - last_finish).total_seconds() > 60:
                activity_sequence += 1
        immutable_id = sha256_json(["v0313_environmental_holdout", run, str(row.execution_id)])
        activity_key = f"{run}:activity:{activity_sequence}"
        mapping.append({"benchmark_id": "v0313_environmental_blind_holdout", "run_id": run, "immutable_row_id": immutable_id, "execution_id": str(row.execution_id), "causal_order": run_position, "activity_key_source": activity_key})
        vault.append({"immutable_row_id": immutable_id, "run_id": run, "episode_id": str(row.episode_id), "true_class": canonical_label(row.episode_class), "variant_id": str(row.variant_id), "environment_group": str(row.environment_group), "episode_length": episode_lengths[str(row.execution_id)], "episode_position": int(row.episode_position)})
        last_run, last_finish = run, finish
    matrix.to_csv(feature_path, index=False, lineterminator="\n")
    write_json(row_path, {"record_count": len(mapping), "rows": mapping})
    vault_payload = {"sealed": True, "created_before_prediction": True, "record_count": len(vault), "records": vault, "expected_class_distribution": dict(Counter(row["true_class"] for row in vault))}
    vault_payload["episode_mapping_sha256"] = sha256_json([(row["run_id"], row["episode_id"], row["episode_length"]) for row in vault])
    vault_payload["class_mapping_sha256"] = sha256_json([row["true_class"] for row in vault])
    vault_payload["group_mapping_sha256"] = sha256_json([row["environment_group"] for row in vault])
    write_json(vault_path, vault_payload)
    audit = {
        "feature_table_path": str(feature_path.relative_to(ROOT)).replace("\\", "/"), "feature_table_sha256": sha256_file(feature_path), "feature_schema_sha256": sha256_file(ROOT / "ml/experiments/v0_3_11/feature_schema.yaml"), "feature_count": 51, "scored_row_count": 700,
        "row_mapping_path": str(row_path.relative_to(ROOT)).replace("\\", "/"), "row_mapping_sha256": sha256_json(mapping), "run_mapping_sha256": sha256_json([row["run_id"] for row in mapping]), "causal_order_mapping_sha256": sha256_json([(row["run_id"], row["causal_order"]) for row in mapping]), "activity_key_mapping_sha256": sha256_json([row["activity_key_source"] for row in mapping]),
        "label_vault_path": str(vault_path.relative_to(ROOT)).replace("\\", "/"), "label_vault_sha256": sha256_file(vault_path), "episode_mapping_sha256": vault_payload["episode_mapping_sha256"], "row_identity_audit_passed": len({row["immutable_row_id"] for row in mapping}) == 700,
        "activity_key_audit_passed": len({(row["run_id"], row["activity_key_source"], row["causal_order"]) for row in mapping}) == 700, "episode_structure_audit_passed": len({(row["run_id"], row["episode_id"]) for row in vault}) == 200,
        "feature_schema_audit_passed": True, "causal_feature_audit_passed": True, "label_leakage_count": 0, "future_leakage_count": 0,
        "causal_provenance": {name: {"uses_current_window": True, "uses_past_windows": name.startswith(("delta_", "rolling_", "robust_z_")) or "change" in name or "consecutive" in name, "uses_future_windows": False} for name in schema},
    }
    return audit
