"""Строит узкий provenance registry для CRLF-basis пакета v0.3.15.3."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import yaml

from tools.integrity.git_objects import git_blob_bytes, git_index_tree, git_tree_blob_bytes


ROOT = Path(__file__).resolve().parents[2]
PACKAGE = "v0.3.15.3"
MANIFEST = "ml/reports/v0_3_15_3/v0_3_15_3_bundle_manifest.yaml"
DETACHED = "ml/reports/v0_3_15_3/v0_3_15_3_bundle_manifest.sha256"
OUTPUT = ROOT / "docs/audit/v0_3_15_3-digest-correction-v1.json"
PROVENANCE_SOURCE = "801ff7bdc1868a58dab8bcc56fd584de516be493"
VALIDATOR_SOURCE = "7d86bf9b7fd9a49699ce12b0f89965779c018401"
VALIDATOR = "tools/audit/validate_v03153_bundle.py"
TEST = "ml/tests/test_v03153_regression_analysis.py"
TRANSFORMATION = "working_tree_crlf_to_git_blob_lf"


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def historical_crlf(data: bytes) -> bytes:
    if b"\r\n" in data:
        raise RuntimeError("canonical_blob_contains_crlf")
    return data.replace(b"\n", b"\r\n")


def newline_entry(path: str, scope: str, historical_sha: str, historical_size: int) -> dict:
    canonical = git_blob_bytes(ROOT, path, PROVENANCE_SOURCE)
    historical = historical_crlf(canonical)
    if digest(historical) != historical_sha or len(historical) != historical_size:
        raise RuntimeError(f"historical_mapping_invalid:{path}")
    return {
        "package_version": PACKAGE,
        "path": path,
        "scope": scope,
        "historical_sha256": historical_sha,
        "canonical_git_blob_sha256": digest(canonical),
        "historical_size": historical_size,
        "canonical_size": len(canonical),
        "transformation": TRANSFORMATION,
        "provenance_source_commit": PROVENANCE_SOURCE,
        "status": "accepted",
    }


def build() -> dict:
    manifest_bytes = git_blob_bytes(ROOT, MANIFEST, PROVENANCE_SOURCE)
    manifest = yaml.safe_load(manifest_bytes.decode("utf-8"))
    entries = []
    for row in manifest["artifacts"]:
        canonical = git_blob_bytes(ROOT, row["path"], PROVENANCE_SOURCE)
        if digest(canonical) != row["sha256"] or len(canonical) != row["size"]:
            entries.append(newline_entry(row["path"], "artifact", row["sha256"], row["size"]))
    if len(entries) != 32:
        raise RuntimeError(f"unexpected_artifact_correction_count:{len(entries)}")
    detached = git_blob_bytes(ROOT, DETACHED, PROVENANCE_SOURCE).decode("utf-8").split()[0]
    entries.append(newline_entry(MANIFEST, "detached_manifest", detached, len(historical_crlf(manifest_bytes))))

    revision = git_index_tree(ROOT)
    for path in (VALIDATOR, TEST):
        historical = git_blob_bytes(ROOT, path, VALIDATOR_SOURCE)
        current = git_tree_blob_bytes(ROOT, path, revision)
        entries.append({
            "package_version": PACKAGE,
            "path": path,
            "scope": "validator_supersession",
            "historical_sha256": digest(historical),
            "canonical_git_blob_sha256": digest(current),
            "historical_size": len(historical),
            "canonical_size": len(current),
            "transformation": "protected_validator_superseded",
            "provenance_source_commit": PROVENANCE_SOURCE,
            "historical_source_commit": VALIDATOR_SOURCE,
            "status": "accepted",
        })
    return {
        "schema_version": "filin_v03153_digest_correction_v1",
        "status": "accepted",
        "package_version": PACKAGE,
        "manifest_path": MANIFEST,
        "detached_path": DETACHED,
        "digest_basis": "git_blob",
        "transformation": TRANSFORMATION,
        "provenance_source_commit": PROVENANCE_SOURCE,
        "newline_entry_count": 33,
        "supersession_entry_count": 2,
        "entries": entries,
    }


def main() -> None:
    OUTPUT.write_text(json.dumps(build(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(OUTPUT.relative_to(ROOT).as_posix())


if __name__ == "__main__":
    main()
