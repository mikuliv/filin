from __future__ import annotations

import io
import json
from pathlib import Path

import joblib
import pandas as pd

from ml.experiments.v0_3_12.frozen_predictor import predict_block
from .blind_access_audit import BlindAccessAudit
from .common import ROOT, read_json, sha256_file, write_json
from .no_fit_guard import NoFitGuard, PredictionGuard


def create_once(artifact: Path, candidate_manifest: Path, feature_path: Path, row_path: Path, lock: dict, output: Path, denied: list[Path]):
    if output.exists():
        payload = read_json(output)
        if payload.get("input_lock_sha256") == lock["input_lock_sha256"] and payload.get("record_count") == 700:
            return payload, {"prediction_generated_once": True, "prediction_generation_count": 1, "prediction_skipped_on_resume": True, "immutable_prediction_sha256": sha256_file(output)}, {"prediction_label_read_count": 0, "prediction_historical_row_read_count": 0, "prediction_historical_prediction_read_count": 0, "prediction_policy_result_read_count": 0, "blind_access_audit_passed": True}
        raise RuntimeError("Существующая prediction не соответствует input lock")
    guard = PredictionGuard()
    guard.authorize(False)
    access = BlindAccessAudit([artifact, candidate_manifest, feature_path, row_path], denied)
    bundle = joblib.load(io.BytesIO(access.read_bytes(artifact)))
    access.read_bytes(candidate_manifest)
    matrix = pd.read_csv(io.BytesIO(access.read_bytes(feature_path)))
    rows = json.loads(access.read_bytes(row_path).decode("utf-8"))["rows"]
    with NoFitGuard() as nofit:
        records, _ = predict_block(bundle, matrix, rows, lock["benchmark_id"])
    for record in records:
        record["joint_probabilities"] = record["joint_class_probabilities"]
        record["transition_reason"] = record["state_transition_reason"]
    records.sort(key=lambda row: (row["run_id"], row["activity_key"], row["causal_order"], row["immutable_row_id"]))
    payload = {"candidate_id": bundle["candidate_id"], "benchmark_id": lock["benchmark_id"], "input_lock_sha256": lock["input_lock_sha256"], "record_count": len(records), "records": records, "true_labels_included": False}
    write_json(output, payload)
    return payload, {**nofit.report(), "prediction_generated_once": True, "prediction_generation_count": guard.count, "prediction_skipped_on_resume": False, "immutable_prediction_sha256": sha256_file(output)}, access.report()
