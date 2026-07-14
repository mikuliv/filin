"""Fail-closed verification of externally stored frozen artifacts."""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from tools.audit.artifact_hashes import file_sha256


DESCRIPTOR_FIELDS = {
    "schema_version", "artifact_type", "external_storage_required",
    "artifact_relative_path", "manifest_relative_path",
    "expected_manifest_schema_version", "expected_artifact_sha256",
    "expected_feature_schema_sha256", "expected_model_class",
    "expected_feature_count", "required_environment_variable",
    "verification_command", "sensitive_content_excluded",
    "historical_artifact_not_corrected_by_audit",
}
SECURE_MANIFEST_FIELDS = {
    "schema_version", "artifact_type", "artifact_relative_path", "artifact_sha256",
    "feature_schema_sha256", "model_class", "feature_count",
}


def _failed(reason: str, artifact_type: str | None = None) -> dict[str, Any]:
    result: dict[str, Any] = {"status": "failed", "passed": False, "reason": reason, "sensitive_content_excluded": True}
    if artifact_type:
        result["artifact_type"] = artifact_type
    return result


def _safe_relative(value: Any) -> Path | None:
    candidate = Path(str(value))
    if candidate.is_absolute() or not candidate.parts or ".." in candidate.parts:
        return None
    return candidate


def _inside_without_symlinks(root: Path, relative: Path) -> Path | None:
    candidate = root / relative
    current = root
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            return None
    try:
        resolved = candidate.resolve(strict=True)
        resolved.relative_to(root)
    except (FileNotFoundError, OSError, ValueError):
        return None
    return resolved


def verify(root: str | None, descriptor_path: Path) -> dict[str, Any]:
    if not root:
        return {
            "status": "not_executed_secure_artifacts_unavailable", "passed": False,
            "reason": "FILIN_SECURE_ARTIFACT_ROOT_unavailable", "sensitive_content_excluded": True,
        }
    try:
        secure_root = Path(root).resolve(strict=True)
    except (FileNotFoundError, OSError):
        return _failed("secure_root_missing")
    if not secure_root.is_dir():
        return _failed("secure_root_not_directory")

    try:
        descriptor = yaml.safe_load(descriptor_path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError):
        return _failed("descriptor_unreadable")
    if not isinstance(descriptor, dict) or set(descriptor) != DESCRIPTOR_FIELDS:
        return _failed("descriptor_schema_mismatch")
    artifact_type = str(descriptor["artifact_type"])
    if descriptor["schema_version"] != 2 or descriptor["required_environment_variable"] != "FILIN_SECURE_ARTIFACT_ROOT":
        return _failed("descriptor_contract_mismatch", artifact_type)
    artifact_relative = _safe_relative(descriptor["artifact_relative_path"])
    manifest_relative = _safe_relative(descriptor["manifest_relative_path"])
    if artifact_relative is None or manifest_relative is None:
        return _failed("unsafe_artifact_reference", artifact_type)
    artifact = _inside_without_symlinks(secure_root, artifact_relative)
    manifest_path = _inside_without_symlinks(secure_root, manifest_relative)
    if artifact is None or not artifact.is_file() or manifest_path is None or not manifest_path.is_file():
        return _failed("missing_or_unsafe_secure_reference", artifact_type)

    try:
        secure_manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError, UnicodeError):
        return _failed("secure_manifest_unreadable", artifact_type)
    if not isinstance(secure_manifest, dict) or set(secure_manifest) != SECURE_MANIFEST_FIELDS:
        return _failed("secure_manifest_schema_mismatch", artifact_type)

    expected_hash = str(descriptor["expected_artifact_sha256"])
    expected_schema_hash = str(descriptor["expected_feature_schema_sha256"])
    hashes_well_formed = all(re.fullmatch(r"[0-9a-f]{64}", value) for value in (expected_hash, expected_schema_hash))
    checks = {
        "manifest_schema": secure_manifest["schema_version"] == descriptor["expected_manifest_schema_version"],
        "artifact_type": secure_manifest["artifact_type"] == artifact_type,
        "artifact_reference": secure_manifest["artifact_relative_path"] == descriptor["artifact_relative_path"],
        "artifact_hash": hashes_well_formed and secure_manifest["artifact_sha256"] == expected_hash == file_sha256(artifact),
        "feature_schema_hash": hashes_well_formed and secure_manifest["feature_schema_sha256"] == expected_schema_hash,
        "model_class": secure_manifest["model_class"] == descriptor["expected_model_class"],
        "feature_count": secure_manifest["feature_count"] == descriptor["expected_feature_count"],
    }
    passed = all(checks.values())
    return {
        "status": "passed" if passed else "failed", "passed": passed,
        "reason": "secure_contract_matches" if passed else "secure_contract_mismatch",
        "artifact_type": artifact_type, "checks": checks, "sensitive_content_excluded": True,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=None)
    parser.add_argument("--descriptor", default="ml/experiments/post_v037_audit/secure_artifact_reference.yaml")
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()
    result = verify(args.root or os.environ.get("FILIN_SECURE_ARTIFACT_ROOT"), Path(args.descriptor))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if args.strict and result["status"] != "passed":
        raise SystemExit(2 if result["status"].startswith("not_executed") else 1)


if __name__ == "__main__":
    main()
