"""Fail-closed проверка frozen-источников v0.3.10."""
from __future__ import annotations
import hashlib
from pathlib import Path
import yaml

FROZEN_PATHS = {
    "protocol": "ml/experiments/v0_3_10/protocol.yaml",
    "data_access_policy": "ml/experiments/v0_3_10/data_access_policy.yaml",
    "training_campaign": "lab/campaigns/v0_3_10_training.yaml",
    "validation_campaign": "lab/campaigns/v0_3_10_internal_validation.yaml",
    "model_selection_policy": "ml/experiments/v0_3_10/model_selection_policy.yaml",
    "validation_policy": "ml/experiments/v0_3_10/internal_validation_policy.yaml",
    "capture_lock_policy": "ml/experiments/v0_3_10/capture_lock_policy.yaml",
    "candidate_artifact": "ml/artifacts/v0_3_10/frozen_candidate.joblib",
    "candidate_manifest": "ml/experiments/v0_3_10/frozen_candidate_manifest.yaml",
    "capture_manifest": "ml/reports/v0_3_10/capture_manifest.json",
    "validation_lock": "ml/experiments/v0_3_10/validation_lock_manifest.yaml",
    "immutable_prediction": "ml/reports/v0_3_10/validation_predictions.json",
}

def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def audit(root: Path, protocol_path: Path) -> dict:
    protocol = yaml.safe_load(protocol_path.read_text(encoding="utf-8"))
    expected = protocol["expected_frozen_hashes"]
    records, valid = {}, True
    for name, relative in FROZEN_PATHS.items():
        path = root / relative
        actual = sha256_file(path) if path.is_file() else None
        matches = actual == expected[name]
        records[name] = {"path": relative, "expected_sha256": expected[name], "actual_sha256": actual, "matches": matches}
        valid = valid and matches
    return {"frozen_integrity_passed": valid, "records": records, "audit_repairs_frozen_files": False}

