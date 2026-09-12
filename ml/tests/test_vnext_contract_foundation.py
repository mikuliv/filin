from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest

from tools.vnext.contracts import (
    CONTRACT_ROOT,
    ContractError,
    SCHEMA_NAMES,
    audit_foundation,
    canonical_bytes,
    canonical_digest,
    load_json,
    validate_recovery_manifest,
    validate_schema_foundation,
    validate_taxonomy,
)


ROOT = Path(__file__).resolve().parents[2]
HISTORICAL_PACKAGES = {
    "official_execution_package.json": ("network-validation-execution-2ae1f6567e7eb4f8", "2ae1f6567e7eb4f8d4829e1ae1210e478763863271b323b16d34095105522492"),
    "official_execution_package_v2.json": ("network-validation-execution-170839c3d8783365", "170839c3d8783365f037dc1c88f85b696b107152f0b39efd437afc236a7a49b4"),
    "official_execution_package_v3.json": ("network-validation-execution-dfbddfe6b9bce845", "dfbddfe6b9bce845d0d218cd8dee29b2763eb5ee03d7ff285dcf780b0b2400cc"),
    "official_execution_package_v4.json": ("network-validation-execution-8e1e32b127893bdf", "8e1e32b127893bdf2e32114b7fb2db19e0e06b2b3de1df5ce2308d2e5571e6cf"),
    "official_execution_package_v5.json": ("network-validation-execution-617f7bc34e59c3f8", "617f7bc34e59c3f8197e29f2ab9dd0394202c17e63a0cf558cb942bd1b2b1066"),
}


def test_all_vnext_schemas_are_closed_versioned_objects() -> None:
    ids = []
    for name in SCHEMA_NAMES:
        schema = load_json(CONTRACT_ROOT / name)
        validate_schema_foundation(schema)
        ids.append(schema["$id"])
    assert len(ids) == len(set(ids))
    assert len(ids) >= 19


def test_taxonomy_is_hierarchical_and_does_not_overstate_coverage() -> None:
    taxonomy = validate_taxonomy(load_json(CONTRACT_ROOT / "behavior_taxonomy_v1.json"))
    ids = {row["node_id"] for row in taxonomy["nodes"]}
    assert {"benign", "malicious"} <= ids
    assert "benign.automation.api_polling" in ids
    assert "malicious.command_and_control.beaconing" in ids
    assert "malicious.collection_exfiltration.dns_tunneling" in ids
    assert "unknown" not in ids
    assert all(row["capability_status"] == "planned" for row in taxonomy["nodes"])


def test_taxonomy_rejects_duplicate_missing_parent_cycle_and_unknown_class() -> None:
    original = load_json(CONTRACT_ROOT / "behavior_taxonomy_v1.json")
    duplicate = deepcopy(original); duplicate["nodes"].append(deepcopy(duplicate["nodes"][0]))
    with pytest.raises(ContractError): validate_taxonomy(duplicate)
    missing = deepcopy(original); missing["nodes"][2]["parent_id"] = "missing"
    with pytest.raises(ContractError): validate_taxonomy(missing)
    unknown = deepcopy(original); unknown["nodes"].append({**deepcopy(unknown["nodes"][0]), "node_id": "unknown"})
    with pytest.raises(ContractError): validate_taxonomy(unknown)


def test_canonical_serialization_is_deterministic_and_rejects_nan() -> None:
    left = {"я": [3, 2, 1], "a": {"z": True, "b": None}}
    right = {"a": {"b": None, "z": True}, "я": [3, 2, 1]}
    assert canonical_bytes(left) == canonical_bytes(right)
    assert canonical_digest(left) == canonical_digest(right)
    with pytest.raises(ValueError): canonical_bytes({"bad": float("nan")})


def test_recovery_manifest_requires_offline_exact_fail_closed_policy() -> None:
    digest = "a" * 64
    value = {
        "schema_version": "execution_recovery_manifest_v1", "recovery_generation": "vnext-1",
        "execution_package": {"package_id": "package", "canonical_digest": digest, "source_commit": "b" * 40},
        "images": [{"logical_name": "sensor", "tag": "filin/sensor:v1", "platform": "linux/amd64", "manifest_digest": "sha256:" + digest, "config_digest": "sha256:" + digest, "base_image_digest": "sha256:" + digest, "build_input_digest": digest, "dockerfile_digest": digest, "source_commit": "b" * 40, "archive_path": "images/sensor.oci", "archive_sha256": digest, "build_metadata": {}}],
        "restore_policy": {"network_pull": "forbidden", "floating_base_images": "forbidden", "automatic_rebuild": "forbidden", "automatic_lock_rewrite": "forbidden", "identity_mismatch": "fail_closed"},
        "verification": {"archive_checksums": True, "loaded_manifest_identity": True, "loaded_config_identity": True, "clean_host_restore_required": True}, "canonical_digest": digest,
    }
    assert validate_recovery_manifest(value) == value
    unsafe = deepcopy(value); unsafe["restore_policy"]["network_pull"] = "allowed"
    with pytest.raises(ContractError): validate_recovery_manifest(unsafe)
    traversal = deepcopy(value); traversal["images"][0]["archive_path"] = "images/../secret.oci"
    with pytest.raises(ContractError): validate_recovery_manifest(traversal)


def test_historical_execution_package_identities_remain_exact() -> None:
    package_root = ROOT / "lab" / "network_validation" / "execution"
    for name, (package_id, package_digest) in HISTORICAL_PACKAGES.items():
        value = json.loads((package_root / name).read_text(encoding="utf-8"))
        assert value["package_id"] == package_id
        assert value.get("canonical_digest", value.get("canonical_payload_sha256")) == package_digest


def test_foundation_audit_is_non_executing() -> None:
    result = audit_foundation()
    assert result["valid"] is True and result["schema_count"] >= 19
    assert result["taxonomy_node_count"] >= 30
    assert result["scientific_execution_performed"] is False
    assert result["historical_artifacts_modified"] is False
