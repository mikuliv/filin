from __future__ import annotations

import hashlib
import json
from pathlib import Path

import yaml


SCHEMA = "v03151_bundle_v1"


class BundleIntegrityError(ValueError):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_manifest_bytes(value: dict) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def load_manifest(path: Path) -> dict:
    try:
        value = yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise BundleIntegrityError("manifest_parse_error") from exc
    if not isinstance(value, dict) or value.get("schema_version") != SCHEMA:
        raise BundleIntegrityError("unknown_schema_version")
    return value


def verify_bundle(manifest_path: str | Path, detached_path: str | Path, *, allowed_root: str | Path | None = None) -> dict:
    manifest_path = Path(manifest_path).resolve()
    detached_path = Path(detached_path).resolve()
    root = Path(allowed_root).resolve() if allowed_root else manifest_path.parent.resolve()
    expected_detached = detached_path.read_text(encoding="ascii").strip().split()[0]
    actual_detached = sha256_file(manifest_path)
    if expected_detached != actual_detached:
        raise BundleIntegrityError("detached_manifest_hash_mismatch")
    manifest = load_manifest(manifest_path)
    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        raise BundleIntegrityError("artifact_list_missing")
    paths = [row.get("path") for row in artifacts]
    if len(paths) != len(set(paths)):
        raise BundleIntegrityError("duplicate_path")
    required_roles = set(manifest.get("required_roles", []))
    actual_roles = {row.get("role") for row in artifacts}
    if not required_roles.issubset(actual_roles):
        raise BundleIntegrityError("required_artifact_missing")
    verified = []
    for row in artifacts:
        relative = Path(str(row.get("path", "")))
        if relative.is_absolute() or ".." in relative.parts:
            raise BundleIntegrityError("path_traversal")
        target = (root / relative).resolve()
        try:
            target.relative_to(root)
        except ValueError as exc:
            raise BundleIntegrityError("path_escape") from exc
        if not target.is_file():
            raise BundleIntegrityError("artifact_missing")
        if target.stat().st_size != row.get("size"):
            raise BundleIntegrityError("artifact_size_mismatch")
        if sha256_file(target) != row.get("sha256"):
            raise BundleIntegrityError("artifact_hash_mismatch")
        verified.append(str(relative).replace("\\", "/"))
    anchors = manifest.get("integrity_anchors", {})
    anchor_roles = {
        "source_prediction_sha256": "source_prediction",
        "event_set_sha256": "event_set",
        "hash_chain_root": "hash_chain",
        "policy_result_sha256": "policy_result",
        "protocol_sha256": "protocol",
        "campaign_sha256": "campaign",
        "contract_schema_sha256": "contract_schema",
        "checkpoint_sha256": "checkpoint",
        "spool_index_sha256": "spool_index",
        "completion_marker_sha256": "completion_marker",
    }
    hashes_by_role = {row.get("role"): row.get("sha256") for row in artifacts}
    for key, role in anchor_roles.items():
        value = anchors.get(key)
        if not isinstance(value, str) or len(value) != 64:
            raise BundleIntegrityError("integrity_anchor_missing:" + key)
        if hashes_by_role.get(role) != value:
            raise BundleIntegrityError("integrity_anchor_mismatch:" + key)
    ledger = manifest.get("claim_evidence")
    if not isinstance(ledger, list) or not ledger or any(not row.get("claim_id") or not row.get("evidence_sha256") for row in ledger):
        raise BundleIntegrityError("claim_evidence_invalid")
    artifact_hashes = {row.get("sha256") for row in artifacts}
    if any(row["evidence_sha256"] not in artifact_hashes for row in ledger):
        raise BundleIntegrityError("claim_evidence_unbound")
    policy = manifest.get("readiness", {})
    if any(policy.get(key) is not False for key in ("production_ready", "backend_integration_ready", "shadow_mode_ready", "automatic_enforcement_ready")):
        raise BundleIntegrityError("unsafe_readiness_flag")
    return {"strict_resume_hash_verification_passed": True, "verified_artifact_count": len(verified), "verified_paths": verified, "manifest_sha256": actual_detached}


def write_detached(manifest_path: str | Path, detached_path: str | Path) -> str:
    digest = sha256_file(Path(manifest_path))
    Path(detached_path).write_text(digest + "  " + Path(manifest_path).name + "\n", encoding="ascii", newline="\n")
    return digest
