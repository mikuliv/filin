"""Строит точечную v2-коррекцию frozen SPDX для заменённого валидатора."""
from __future__ import annotations

import json
from pathlib import Path

from .common import ROOT, canonical_sha256, index_sha256_many


SOURCE_MAPPING_COMMIT = "801ff7bdc1868a58dab8bcc56fd584de516be493"
SUPERSEDING_COMMIT = "FINAL_LICENSING_COMMIT_SELF_REFERENCE"
TARGET = "tools/audit/validate_v03154_bundle.py"
OLD_SHA256 = "ff8b7b72b62e85077b8df2dbc0d244d72f4d849ce68f66fd7e81bd177cee58dd"
CORRECTION_PATH = ROOT / "docs/licensing/frozen-spdx-mapping-correction-v2.json"


def build(root: Path = ROOT) -> dict:
    payload = {
        "schema_version": "filin_frozen_spdx_mapping_correction_v2",
        "status": "accepted",
        "correction_date": "2026-09-13",
        "source_mapping_commit": SOURCE_MAPPING_COMMIT,
        "source_mapping_sha256": canonical_sha256(
            root, "docs/licensing/frozen-spdx-mapping.json", SOURCE_MAPPING_COMMIT
        ),
        "superseding_commit": SUPERSEDING_COMMIT,
        "digest_basis": "git_blob",
        "reason": "Явная замена валидатора для канонической Git-blob проверки без изменения научных результатов.",
        "entry_count": 1,
        "entries": [{
            "path": TARGET,
            "correction_kind": "protected_validator_superseded",
            "old_stored_sha256": OLD_SHA256,
            "old_digest_basis": "git_blob",
            "canonical_git_blob_sha256": index_sha256_many(root, [TARGET])[TARGET],
            "license_expression": "MPL-2.0",
            "copyright_holder": "Руслан Покатилов",
            "file_type": "source_or_configuration",
            "assignment_source": "reuse_toml",
            "status": "accepted",
        }],
    }
    CORRECTION_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return payload


if __name__ == "__main__":
    value = build()
    print(json.dumps({"entry_count": value["entry_count"], "digest_basis": value["digest_basis"]}, ensure_ascii=False))
