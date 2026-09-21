from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

import yaml

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.integrity.git_objects import (
    GitObjectError,
    git_blob_bytes,
    git_commit,
    git_index_tree,
    git_tree_blob_bytes,
)


PACKAGE_VERSION = "v0.3.15.3"
MANIFEST_PATH = "ml/reports/v0_3_15_3/v0_3_15_3_bundle_manifest.yaml"
DETACHED_PATH = "ml/reports/v0_3_15_3/v0_3_15_3_bundle_manifest.sha256"
CORRECTION_PATH = "docs/audit/v0_3_15_3-digest-correction-v1.json"
VALIDATOR_PATH = "tools/audit/validate_v03153_bundle.py"
TEST_PATH = "ml/tests/test_v03153_regression_analysis.py"
CORRECTION_SCHEMA = "filin_v03153_digest_correction_v1"
CRLF_TRANSFORMATION = "working_tree_crlf_to_git_blob_lf"
VALIDATOR_TRANSFORMATION = "protected_validator_superseded"
EXPECTED_NEWLINE_CORRECTIONS = 33
EXPECTED_SUPERSESSIONS = 2
SUPERSEDED_PATHS = {VALIDATOR_PATH, TEST_PATH}

REQUIRED_ROLES = {
    "policy_result", "summary", "historical_integrity", "evidence_inventory",
    "episode_ledger", "root_cause_matrix", "claim_ledger", "test_report",
    "protocol", "proposed_protocol",
}
FORBIDDEN_PARTS = {"runtime", "pcap", "zeek", "spool", "checkpoint", "raw_ack", "label_vault", "feature_rows", "immutable_predictions"}


class CorrectionError(RuntimeError):
    """Correction отсутствует, неоднозначна или не подтверждает обе representation."""


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _repository_path(root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(root).as_posix()
    except ValueError as exc:
        raise CorrectionError(f"path_confinement:{path}") from exc


def _historical_crlf(canonical: bytes) -> bytes:
    if b"\r\n" in canonical:
        raise CorrectionError("canonical_blob_contains_crlf")
    return canonical.replace(b"\n", b"\r\n")


def validate_declared_correction(
    entry: dict[str, Any] | None,
    *,
    path: str,
    scope: str,
    historical_sha256: str,
    historical_size: int,
    canonical: bytes,
) -> None:
    """Проверяет одну allowlist-запись; без записи нормализация запрещена."""
    if entry is None:
        raise CorrectionError(f"correction_missing:{path}")
    expected = {
        "package_version": PACKAGE_VERSION,
        "path": path,
        "scope": scope,
        "historical_sha256": historical_sha256,
        "historical_size": historical_size,
        "canonical_git_blob_sha256": _sha(canonical),
        "canonical_size": len(canonical),
        "transformation": CRLF_TRANSFORMATION,
        "status": "accepted",
    }
    for key, value in expected.items():
        if entry.get(key) != value:
            raise CorrectionError(f"correction_{key}_mismatch:{path}")
    historical = _historical_crlf(canonical)
    if len(historical) != historical_size:
        raise CorrectionError(f"correction_historical_size_mismatch:{path}")
    if _sha(historical) != historical_sha256:
        raise CorrectionError(f"correction_historical_digest_mismatch:{path}")


def _load_corrections(root: Path, revision: str) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    raw = git_tree_blob_bytes(root, CORRECTION_PATH, revision)
    registry = json.loads(raw.decode("utf-8"))
    source_commit = registry.get("provenance_source_commit", "")
    if (
        registry.get("schema_version") != CORRECTION_SCHEMA
        or registry.get("status") != "accepted"
        or registry.get("package_version") != PACKAGE_VERSION
        or registry.get("manifest_path") != MANIFEST_PATH
        or registry.get("detached_path") != DETACHED_PATH
        or registry.get("digest_basis") != "git_blob"
        or registry.get("transformation") != CRLF_TRANSFORMATION
        or registry.get("newline_entry_count") != EXPECTED_NEWLINE_CORRECTIONS
        or registry.get("supersession_entry_count") != EXPECTED_SUPERSESSIONS
    ):
        raise CorrectionError("correction_registry_header_invalid")
    git_commit(root, source_commit)
    entries = registry.get("entries", [])
    if len(entries) != EXPECTED_NEWLINE_CORRECTIONS + EXPECTED_SUPERSESSIONS:
        raise CorrectionError("correction_registry_count_invalid")
    indexed: dict[str, dict[str, Any]] = {}
    for entry in entries:
        path = entry.get("path")
        if not isinstance(path, str) or path in indexed:
            raise CorrectionError("correction_registry_path_invalid")
        if entry.get("provenance_source_commit") != source_commit:
            raise CorrectionError(f"correction_source_commit_mismatch:{path}")
        indexed[path] = entry
    return indexed, registry


def _validate_newline_entry(root: Path, revision: str, source_commit: str, entry: dict[str, Any]) -> bytes:
    path = entry["path"]
    canonical = git_tree_blob_bytes(root, path, revision)
    source = git_blob_bytes(root, path, source_commit)
    if source != canonical:
        raise CorrectionError(f"correction_source_blob_mismatch:{path}")
    validate_declared_correction(
        entry,
        path=path,
        scope=entry.get("scope", ""),
        historical_sha256=entry.get("historical_sha256", ""),
        historical_size=entry.get("historical_size", -1),
        canonical=canonical,
    )
    return canonical


def _validate_supersession(root: Path, revision: str, path: str, entry: dict[str, Any], row: dict[str, Any]) -> None:
    source_commit = entry.get("historical_source_commit", "")
    git_commit(root, source_commit)
    historical = git_blob_bytes(root, path, source_commit)
    canonical = git_tree_blob_bytes(root, path, revision)
    expected = {
        "package_version": PACKAGE_VERSION,
        "path": path,
        "scope": "validator_supersession",
        "historical_sha256": row.get("sha256"),
        "historical_size": row.get("size"),
        "canonical_git_blob_sha256": _sha(canonical),
        "canonical_size": len(canonical),
        "transformation": VALIDATOR_TRANSFORMATION,
        "status": "accepted",
    }
    for key, value in expected.items():
        if entry.get(key) != value:
            raise CorrectionError(f"validator_{key}_mismatch")
    if _sha(historical) != row.get("sha256") or len(historical) != row.get("size"):
        raise CorrectionError("validator_historical_blob_mismatch")


def validate(manifest_path: str | Path, detached_path: str | Path, root: str | Path) -> dict:
    root = Path(root).resolve()
    errors: list[str] = []
    used: set[str] = set()
    supersessions_used = 0
    try:
        manifest_relative = _repository_path(root, Path(manifest_path))
        detached_relative = _repository_path(root, Path(detached_path))
        if manifest_relative != MANIFEST_PATH or detached_relative != DETACHED_PATH:
            raise CorrectionError("bundle_path_scope_invalid")
        revision = git_index_tree(root)
        manifest_bytes = git_tree_blob_bytes(root, MANIFEST_PATH, revision)
        detached_bytes = git_tree_blob_bytes(root, DETACHED_PATH, revision)
        manifest = yaml.safe_load(manifest_bytes.decode("utf-8"))
        detached = detached_bytes.decode("utf-8").split()[0]
        corrections, registry = _load_corrections(root, revision)
        source_commit = registry["provenance_source_commit"]
        for entry in corrections.values():
            if entry.get("transformation") == CRLF_TRANSFORMATION:
                _validate_newline_entry(root, revision, source_commit, entry)
            elif entry.get("transformation") != VALIDATOR_TRANSFORMATION:
                raise CorrectionError(f"correction_transformation_unknown:{entry.get('path', '')}")
    except (CorrectionError, GitObjectError, OSError, UnicodeDecodeError, json.JSONDecodeError, yaml.YAMLError, KeyError) as exc:
        return {
            "schema_version": "v03153_bundle_validation_v2",
            "artifact_count": 0,
            "correction_records_used": 0,
            "supersession_records_used": 0,
            "error_count": 1,
            "errors": [f"correction_registry:{exc}"],
            "bundle_validator_passed": False,
        }

    if manifest.get("schema_version") != "v03153_bundle_v1":
        errors.append("schema")
    manifest_correction = corrections.get(MANIFEST_PATH)
    try:
        validate_declared_correction(
            manifest_correction,
            path=MANIFEST_PATH,
            scope="detached_manifest",
            historical_sha256=detached,
            historical_size=manifest_correction.get("historical_size", -1) if manifest_correction else -1,
            canonical=manifest_bytes,
        )
        used.add(MANIFEST_PATH)
    except CorrectionError as exc:
        errors.append(f"detached_sha:{exc}")

    artifacts = manifest.get("artifacts", [])
    paths = [row.get("path") for row in artifacts]
    if len(paths) != len(set(paths)):
        errors.append("duplicate_paths")
    roles = {row.get("role") for row in artifacts}
    if not REQUIRED_ROLES <= roles:
        errors.append("required_roles")

    try:
        claims_bytes = git_tree_blob_bytes(root, "ml/reports/v0_3_15_3/claim_evidence_ledger.json", revision)
        claims = {row["claim_id"] for row in json.loads(claims_bytes.decode("utf-8"))["claims"]}
    except (GitObjectError, UnicodeDecodeError, json.JSONDecodeError, KeyError) as exc:
        errors.append(f"claims:{exc}")
        claims = set()

    for row in artifacts:
        relative = row.get("path", "")
        try:
            content = git_tree_blob_bytes(root, relative, revision)
        except GitObjectError as exc:
            errors.append(f"canonical_blob:{relative}:{exc}")
            continue
        if relative in SUPERSEDED_PATHS:
            try:
                _validate_supersession(root, revision, relative, corrections.get(relative, {}), row)
                supersessions_used += 1
            except (CorrectionError, GitObjectError) as exc:
                errors.append(f"validator_supersession:{exc}")
        elif len(content) != row.get("size") or _sha(content) != row.get("sha256"):
            try:
                validate_declared_correction(
                    corrections.get(relative),
                    path=relative,
                    scope="artifact",
                    historical_sha256=row.get("sha256", ""),
                    historical_size=row.get("size", -1),
                    canonical=content,
                )
                used.add(relative)
            except CorrectionError as exc:
                errors.append(f"historical_digest:{relative}:{exc}")
        if not set(row.get("claim_ids", [])) <= claims:
            errors.append(f"claim_reference:{relative}")
        lowered = relative.lower()
        if any(part in lowered.split("/") for part in FORBIDDEN_PARTS):
            errors.append(f"raw_artifact:{relative}")
        if row.get("role") not in {"behavioral_tests", "instrumentation_code", "bundle_validator", "artifact_validator", "ack_contract"}:
            text = content.decode("utf-8", errors="ignore")
            if re.search(r"[A-Za-z]:\\(?:Users|home)\\", text):
                errors.append(f"absolute_path:{relative}")
            if re.search(r"(?i)(?:token|password|secret)\s*[=:]\s*[^\s\"']{6,}", text):
                errors.append(f"secret:{relative}")

    newline_paths = {path for path, entry in corrections.items() if entry.get("transformation") == CRLF_TRANSFORMATION}
    if used != newline_paths:
        errors.append("correction_usage_incomplete")
    if supersessions_used != EXPECTED_SUPERSESSIONS:
        errors.append("supersession_usage_incomplete")

    try:
        policy_bytes = git_tree_blob_bytes(root, "ml/reports/v0_3_15_3/v0_3_15_3_policy_result.json", revision)
        policy = json.loads(policy_bytes.decode("utf-8"))
    except (GitObjectError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        errors.append(f"policy:{exc}")
        policy = {}
    for key in ["candidate_ready_for_v0_3_16_staging_connector_readiness", "candidate_ready_for_shadow_mode", "sensor_ready_for_backend_integration", "production_ready", "automatic_enforcement_ready", "external_validation_completed"]:
        if policy.get(key) is not False:
            errors.append(f"readiness:{key}")
    anchors = manifest.get("historical_anchors", {})
    if anchors.get("v03152_bundle_manifest_sha256") != "49e13eceb44873f593844b07d86215b36dffd96be7ebbbb75a004c08bad8dcda":
        errors.append("historical_anchor")
    return {
        "schema_version": "v03153_bundle_validation_v2",
        "artifact_count": len(artifacts),
        "correction_records_used": len(used),
        "supersession_records_used": supersessions_used,
        "error_count": len(errors),
        "errors": errors,
        "bundle_validator_passed": not errors,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--detached", required=True)
    parser.add_argument("--root", default=".")
    args = parser.parse_args()
    result = validate(args.manifest, args.detached, args.root)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    raise SystemExit(0 if result["bundle_validator_passed"] else 1)


if __name__ == "__main__":
    main()
