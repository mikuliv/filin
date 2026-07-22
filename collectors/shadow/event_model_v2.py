from __future__ import annotations

import hashlib
from .canonical import canonical_bytes
from .candidate_registry import load_registry


def _digest(*parts: object) -> str:
    return hashlib.sha256("|".join(map(str, parts)).encode()).hexdigest()


def generate_event(*, event_type: str, session_id: str, source_sequence: int, activity_key: str, prediction: dict, payload: dict, previous_hash: str | None = None) -> dict:
    registry, commitment = load_registry()
    candidate = next(item for item in registry["candidates"] if item["candidate_id"] == "v03154:65a3dd912d845bc1")
    identity = _digest(session_id, source_sequence, prediction["prediction_id"], event_type)
    return {
        "schema_version": "shadow_event_v2", "event_contract_version": "shadow_event_v2",
        "event_id": "evt_" + identity, "event_type": event_type, "event_timestamp": "2026-07-22T00:00:00Z",
        "causal_order": source_sequence, "activity_key": activity_key, "idempotency_key": _digest("delivery", identity),
        "candidate_ref": {
            "candidate_id": candidate["candidate_id"], "artifact_sha256": candidate["artifact_sha256"], "manifest_sha256": candidate["manifest_sha256"],
            "feature_contract_id": candidate["feature_contract_id"], "feature_contract_sha256": candidate["feature_contract_sha256"],
            "preprocessing_sha256": candidate["preprocessing_sha256"], "calibration_sha256": candidate["calibration_sha256"],
            "conformal_sha256": candidate["conformal_sha256"], "state_policy_sha256": candidate["state_policy_sha256"],
            "registry_commitment_sha256": commitment["candidate_registry_commitment_sha256"]},
        "prediction_ref": {key: prediction[key] for key in ("prediction_id", "prediction_sha256", "source_capture_id", "source_capture_sha256", "feature_row_id", "feature_row_sha256")},
        "runtime_ref": {"session_id": session_id, "runtime_instance_id": "rti_" + _digest("runtime", session_id), "source_sequence": source_sequence, "hash_chain_previous": previous_hash, "runtime_contract_version": "passive_runtime_v031551"},
        "payload": payload,
    }
