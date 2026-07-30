from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from .contracts import ContractError


def validate_candidate_identity(artifact: Path, internal_metadata: dict[str, Any], external_manifest: dict[str, Any], expected_feature_order_digest: str) -> None:
    actual_sha = hashlib.sha256(artifact.read_bytes()).hexdigest()
    required = {"candidate_id", "artifact_sha256", "feature_order_digest"}
    if set(internal_metadata) != required or set(external_manifest) != required:
        raise ContractError("candidate identity fields mismatch")
    if internal_metadata != external_manifest:
        raise ContractError("internal/external candidate identity mismatch")
    if external_manifest["artifact_sha256"] != actual_sha:
        raise ContractError("candidate artifact SHA mismatch")
    if external_manifest["candidate_id"] != f"candidate:{actual_sha[:16]}":
        raise ContractError("candidate ID is not based on final serialization")
    if external_manifest["feature_order_digest"] != expected_feature_order_digest:
        raise ContractError("candidate feature order mismatch")
