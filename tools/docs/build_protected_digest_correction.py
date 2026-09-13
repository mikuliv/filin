"""Фиксирует явную LF/CRLF-коррекцию реестра protected documentation."""
from __future__ import annotations

import json
from pathlib import Path

from tools.docs.documentation_v2 import ROOT
from tools.integrity.git_objects import git_blob_bytes, git_blob_sha256, git_blob_sha256_many


SOURCE_REGISTRY_COMMIT = "bb5f5d94ce7543d0a0b271e4deded2f16c487dd7"
REGISTRY_PATH = "docs/audit/protected_documentation_v2.json"
CORRECTION_PATH = ROOT / "docs/audit/protected-documentation-digest-correction-v1.json"


def build(root: Path = ROOT) -> dict:
    source_bytes = git_blob_bytes(root, REGISTRY_PATH, SOURCE_REGISTRY_COMMIT)
    registry = json.loads(source_bytes.decode("utf-8"))
    current = git_blob_sha256_many(root, [row["path"] for row in registry["files"]], "HEAD")
    entries = []
    for row in registry["files"]:
        path = row["path"]
        canonical = current[path]
        if canonical != row.get("actual_sha256"):
            is_eol_basis = path.endswith(".sha256")
            entries.append({
                "path": path,
                "old_stored_sha256": row.get("actual_sha256"),
                "correction_kind": "digest_basis_corrected" if is_eol_basis else "protected_validator_superseded",
                "old_digest_basis": "working_tree_crlf" if is_eol_basis else "git_blob",
                "canonical_git_blob_sha256": canonical,
                "reason": "Канонизация basis detached SHA." if is_eol_basis else "Санкционированная замена validator для разрешения immutable snapshot через Git blob.",
                "status": "accepted",
            })
    unexpected = [row["path"] for row in entries if not row["path"].endswith(".sha256") and row["path"] != "tools/audit/validate_v03154_bundle.py"]
    if len(entries) != 24 or unexpected:
        raise RuntimeError("protected_digest_correction_incomplete")
    payload = {
        "schema_version": "filin_protected_documentation_digest_correction_v1",
        "status": "accepted",
        "correction_date": "2026-09-13",
        "source_registry_commit": SOURCE_REGISTRY_COMMIT,
        "source_registry_sha256": git_blob_sha256(root, REGISTRY_PATH, SOURCE_REGISTRY_COMMIT),
        "correction_commit": "FINAL_LICENSING_COMMIT_SELF_REFERENCE",
        "digest_basis": "git_blob",
        "reason": "Исправление basis для 23 detached SHA и явная санкционированная замена одного historical validator без изменения scientific outputs.",
        "entry_count": len(entries),
        "entries": sorted(entries, key=lambda row: row["path"]),
    }
    (root / REGISTRY_PATH).write_bytes(source_bytes)
    CORRECTION_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    from tools.docs.documentation_v2 import build_protected_set
    protected = build_protected_set(root)
    (root / REGISTRY_PATH).write_text(
        json.dumps({
            "schema_version": "filin_protected_documentation_v2",
            "source_strategy": "manifests_ledgers_protocols_and_detached_sha",
            "files": protected,
        }, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return payload


if __name__ == "__main__":
    value = build()
    print(json.dumps({"entry_count": value["entry_count"], "digest_basis": value["digest_basis"]}, ensure_ascii=False))
