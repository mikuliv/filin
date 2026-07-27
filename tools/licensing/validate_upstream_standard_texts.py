"""Validate immutable upstream license and contributor-certificate texts offline."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .common import HOLDER, ROOT, UPSTREAM_STANDARD_TEXTS, dump, finish, parser


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def registry_payload(root: Path = ROOT, manifest: dict[str, Any] | None = None) -> dict[str, Any]:
    if manifest is None:
        manifest = json.loads((root / "licensing/repository-license-manifest.json").read_text(encoding="utf-8"))
    indexed = {row["path"]: row for row in manifest.get("files", [])}
    rows = []
    for path, expected in UPSTREAM_STANDARD_TEXTS.items():
        row = indexed.get(path, {})
        actual = digest(root / path) if (root / path).is_file() else None
        rows.append({
            "path": path, "sha256": actual, "expected_sha256": expected["sha256"],
            "document_kind": expected["document_kind"], "upstream_name": expected["upstream_name"],
            "upstream_copyright_holder": expected["upstream_copyright_holder"],
            "upstream_reference": expected["upstream_reference"],
            "license_expression": expected["license_expression"],
            "ownership": row.get("ownership"), "third_party": row.get("third_party"),
            "project_authored": row.get("project_authored"),
            "upstream_standard_text": row.get("upstream_standard_text"),
            "assignment_source": row.get("assignment_source"),
            "text_modified": actual != expected["sha256"],
            "included_for_compliance": row.get("included_for_compliance"),
            "text_modification_allowed": row.get("text_modification_allowed"),
            "distribution_profiles": row.get("distribution_profiles", []),
        })
    return {"schema_version": "filin_upstream_standard_texts_v1_1", "count": len(rows), "official_license_text_changed_count": sum(r["text_modified"] for r in rows), "texts": rows}


def validate(root: Path = ROOT) -> list[dict[str, Any]]:
    errors: list[dict[str, Any]] = []
    manifest_path = root / "licensing/repository-license-manifest.json"
    if not manifest_path.is_file():
        return [{"code": "repository_manifest_missing"}]
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    indexed = {row.get("path"): row for row in manifest.get("files", [])}
    reuse = (root / "REUSE.toml").read_text(encoding="utf-8") if (root / "REUSE.toml").is_file() else ""
    for path, expected in UPSTREAM_STANDARD_TEXTS.items():
        target = root / path
        if not target.is_file():
            errors.append({"code": "upstream_standard_text_missing", "path": path}); continue
        actual = digest(target)
        if actual != expected["sha256"]:
            errors.append({"code": "official_standard_text_modified", "path": path, "actual": actual})
        head = target.read_bytes()[:512].decode("utf-8", errors="ignore")
        if "SPDX-FileCopyrightText:" in head or "SPDX-License-Identifier:" in head:
            errors.append({"code": "spdx_header_inside_official_text", "path": path})
        row = indexed.get(path)
        if not row:
            errors.append({"code": "upstream_standard_text_manifest_entry_missing", "path": path}); continue
        checks = [
            (row.get("ownership") == "upstream_standard_text", "upstream_text_ownership_invalid"),
            (row.get("third_party") is True, "upstream_text_third_party_invalid"),
            (row.get("project_authored") is False, "upstream_text_project_authored_conflict"),
            (row.get("upstream_standard_text") is True, "upstream_text_marker_missing"),
            (row.get("included_for_compliance") is True, "upstream_text_compliance_marker_missing"),
            (row.get("text_modification_allowed") is False, "upstream_text_mutability_invalid"),
            (row.get("assignment_source") == "upstream_license", "upstream_text_assignment_source_invalid"),
            (row.get("copyright_holder") == expected["upstream_copyright_holder"], "upstream_holder_invalid"),
            (row.get("license_expression") == expected["license_expression"], "upstream_license_expression_invalid"),
        ]
        for passed, code in checks:
            if not passed: errors.append({"code": code, "path": path})
        if row.get("copyright_holder") == HOLDER:
            errors.append({"code": "project_holder_claimed_for_upstream_text", "path": path})
        if path not in reuse:
            errors.append({"code": "reuse_upstream_path_missing", "path": path})
        if expected["upstream_copyright_holder"] not in reuse:
            errors.append({"code": "reuse_upstream_holder_missing", "path": path})
    discovered = {row.get("path") for row in manifest.get("files", []) if row.get("assignment_source") == "upstream_license" or row.get("file_type") in {"license_text", "policy_text"}}
    for path in sorted(discovered - set(UPSTREAM_STANDARD_TEXTS)):
        errors.append({"code": "unknown_upstream_standard_text", "path": path})
    if (root / "LICENSE").is_file() and (root / "LICENSES/MPL-2.0.txt").is_file() and (root / "LICENSE").read_bytes() != (root / "LICENSES/MPL-2.0.txt").read_bytes():
        errors.append({"code": "root_mpl_copy_mismatch"})
    return errors


def write_registry(root: Path = ROOT, manifest: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = registry_payload(root, manifest)
    dump("docs/licensing/upstream-standard-texts.json", payload)
    lines = ["# Официальные upstream standard texts", "", "Официальные тексты MPL-2.0, CC BY 4.0 и DCO 1.1 включены в репозиторий как неизменённые upstream standard texts. Их включение не означает, что автор проекта является автором этих стандартных текстов.", "", "| Файл | Вид | Upstream | SHA-256 | Лицензия файла | Изменён |", "|---|---|---|---|---|---|"]
    for row in payload["texts"]:
        lines.append(f"| `{row['path']}` | `{row['document_kind']}` | {row['upstream_name']} | `{row['sha256']}` | `{row['license_expression']}` | {'да' if row['text_modified'] else 'нет'} |")
    lines += ["", "`LICENSE` и `LICENSES/MPL-2.0.txt` намеренно содержат одну и ту же официальную копию MPL-2.0: корневой файл обозначает основную программную лицензию, а копия в `LICENSES/` обеспечивает REUSE layout.", ""]
    (root / "docs/licensing/upstream-standard-texts.md").write_text("\n".join(lines), encoding="utf-8")
    return payload


def main() -> int:
    args = parser(__doc__).parse_args(); errors = validate(args.root)
    details = registry_payload(args.root) if (args.root / "licensing/repository-license-manifest.json").is_file() else {}
    return finish("validate_upstream_standard_texts", errors, {"upstream_standard_text_count": details.get("count", 0), "official_license_text_changed_count": details.get("official_license_text_changed_count")}, args.strict)


if __name__ == "__main__": raise SystemExit(main())
