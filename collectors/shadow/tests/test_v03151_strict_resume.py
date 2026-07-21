from __future__ import annotations

import hashlib
import json
import shutil

import pytest
import yaml

from tools.audit.strict_bundle import BundleIntegrityError, verify_bundle, write_detached


ROLES = ["source_prediction", "event_set", "hash_chain", "policy_result", "protocol", "campaign", "contract_schema", "checkpoint", "spool_index", "completion_marker", "claim_ledger"]
ANCHORS = {
    "source_prediction_sha256": "source_prediction", "event_set_sha256": "event_set", "hash_chain_root": "hash_chain",
    "policy_result_sha256": "policy_result", "protocol_sha256": "protocol", "campaign_sha256": "campaign",
    "contract_schema_sha256": "contract_schema", "checkpoint_sha256": "checkpoint", "spool_index_sha256": "spool_index",
    "completion_marker_sha256": "completion_marker",
}


def create_bundle(root):
    artifacts = []
    digests = {}
    for role in ROLES:
        path = root / f"{role}.json"
        path.write_text(json.dumps({"role": role}, sort_keys=True) + "\n", encoding="utf-8")
        digest = hashlib.sha256(path.read_bytes()).hexdigest(); digests[role] = digest
        artifacts.append({"role": role, "path": path.name, "size": path.stat().st_size, "sha256": digest})
    manifest = {
        "schema_version": "v03151_bundle_v1",
        "artifacts": artifacts,
        "required_roles": ROLES,
        "integrity_anchors": {key: digests[role] for key, role in ANCHORS.items()},
        "claim_evidence": [{"claim_id": "fixture", "evidence_sha256": digests["claim_ledger"]}],
        "readiness": {"production_ready": False, "backend_integration_ready": False, "shadow_mode_ready": False, "automatic_enforcement_ready": False},
    }
    manifest_path = root / "manifest.yaml"
    manifest_path.write_text(yaml.safe_dump(manifest, sort_keys=True), encoding="utf-8")
    detached = root / "manifest.sha256"; write_detached(manifest_path, detached)
    return manifest_path, detached


def test_strict_resume_verifies_every_hash_and_size(tmp_path):
    manifest, detached = create_bundle(tmp_path)
    result = verify_bundle(manifest, detached)
    assert result["verified_artifact_count"] == len(ROLES)


@pytest.mark.parametrize("case", ["changed_byte", "removed", "replaced_policy", "event_set", "hash_chain", "source_prediction", "spool", "checkpoint"])
def test_corrupted_bundle_is_rejected(tmp_path, case):
    manifest, detached = create_bundle(tmp_path)
    role = {"changed_byte":"protocol", "removed":"campaign", "replaced_policy":"policy_result", "event_set":"event_set", "hash_chain":"hash_chain", "source_prediction":"source_prediction", "spool":"spool_index", "checkpoint":"checkpoint"}[case]
    path = tmp_path / f"{role}.json"
    if case == "removed": path.unlink()
    else: path.write_bytes(path.read_bytes() + b"x")
    with pytest.raises(BundleIntegrityError): verify_bundle(manifest, detached)


def test_path_traversal_is_rejected(tmp_path):
    manifest, detached = create_bundle(tmp_path)
    value = yaml.safe_load(manifest.read_text()); value["artifacts"][0]["path"] = "../escape.json"
    manifest.write_text(yaml.safe_dump(value)); write_detached(manifest, detached)
    with pytest.raises(BundleIntegrityError, match="path_traversal"): verify_bundle(manifest, detached)


def test_duplicate_path_is_rejected(tmp_path):
    manifest, detached = create_bundle(tmp_path)
    value = yaml.safe_load(manifest.read_text()); value["artifacts"][1]["path"] = value["artifacts"][0]["path"]
    manifest.write_text(yaml.safe_dump(value)); write_detached(manifest, detached)
    with pytest.raises(BundleIntegrityError, match="duplicate_path"): verify_bundle(manifest, detached)


def test_unknown_schema_is_rejected(tmp_path):
    manifest, detached = create_bundle(tmp_path)
    value = yaml.safe_load(manifest.read_text()); value["schema_version"] = "future"
    manifest.write_text(yaml.safe_dump(value)); write_detached(manifest, detached)
    with pytest.raises(BundleIntegrityError, match="unknown_schema_version"): verify_bundle(manifest, detached)


def test_detached_manifest_lock_rejects_manifest_change(tmp_path):
    manifest, detached = create_bundle(tmp_path)
    manifest.write_text(manifest.read_text() + "#changed\n")
    with pytest.raises(BundleIntegrityError, match="detached_manifest_hash_mismatch"): verify_bundle(manifest, detached)
