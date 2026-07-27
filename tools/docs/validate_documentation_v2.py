"""Главный строгий validator Documentation v2."""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import yaml

from tools.docs.documentation_v2 import (
    ABSOLUTE_RE, BACKEND_TREE, CANDIDATE_ID, HEADING_RE, INITIAL_HEAD, REQUIRED_CURRENT_DOCS,
    REQUIRED_ROOTS, REQUIRED_SUBSYSTEM_READMES, ROOT, SECRET_RES, build_protected_set,
    front_matter, github_anchors, inventory_rows, link_findings, local_links, run_git,
    sha256, tracked_markdown,
)


REQUIRED_FRONT_MATTER = {
    "doc_schema", "title", "document_type", "audience", "lifecycle",
    "authoritative_for", "source_of_truth", "last_reviewed_stage", "generated",
    "evidence_immutable",
}
MERMAID_START = ("flowchart", "graph", "sequenceDiagram", "stateDiagram", "classDiagram", "erDiagram", "journey", "gantt", "pie", "mindmap", "timeline")


def error(code: str, path: str = "", detail: str = "") -> str:
    return ":".join(value for value in (code, path, detail) if value)


def current_mutable(path: Path, protected: set[str], root: Path) -> bool:
    relative = path.relative_to(root).as_posix()
    if relative in protected:
        return False
    metadata = front_matter(path)
    return metadata.get("lifecycle") in {"current", "generated", "redirect"} or relative.endswith("README.md")


def validate_headings(path: Path, root: Path) -> list[str]:
    relative = path.relative_to(root).as_posix()
    headings = [(len(level), title) for level, title in HEADING_RE.findall(path.read_text(encoding="utf-8"))]
    errors = []
    h1 = sum(level == 1 for level, _ in headings)
    if h1 != 1:
        errors.append(error("h1_count", relative, str(h1)))
    for (left, _), (right, _) in zip(headings, headings[1:]):
        if right > left + 1:
            errors.append(error("heading_jump", relative, f"{left}->{right}"))
    return errors


def validate_mermaid(path: Path, root: Path) -> list[str]:
    relative = path.relative_to(root).as_posix()
    text = path.read_text(encoding="utf-8")
    errors: list[str] = []
    if text.count("```mermaid") != len(re.findall(r"```mermaid\s*\n.*?\n```", text, re.DOTALL)):
        errors.append(error("invalid_mermaid_fence", relative))
    for block in re.findall(r"```mermaid\s*\n(.*?)\n```", text, re.DOTALL):
        first = next((line.strip() for line in block.splitlines() if line.strip()), "")
        if not first.startswith(MERMAID_START):
            errors.append(error("invalid_mermaid_declaration", relative, first))
    return errors


def validate_redirects(markdown: list[Path], root: Path) -> list[str]:
    targets: dict[str, str] = {}
    errors: list[str] = []
    for path in markdown:
        meta = front_matter(path)
        if meta.get("lifecycle") != "redirect":
            continue
        relative = path.relative_to(root).as_posix()
        target = meta.get("redirect_target")
        if not isinstance(target, str) or not target:
            errors.append(error("redirect_target_missing", relative)); continue
        resolved = (path.parent / target).resolve()
        try:
            target_relative = resolved.relative_to(root.resolve()).as_posix()
        except ValueError:
            errors.append(error("redirect_escapes_repository", relative)); continue
        if not resolved.is_file():
            errors.append(error("redirect_target_broken", relative, target)); continue
        targets[relative] = target_relative
        lower = path.read_text(encoding="utf-8").casefold()
        if any(phrase in lower for phrase in ("production_ready: true", "backend integration allowed: true", "v0.4.x планируется")):
            errors.append(error("redirect_old_capability_marker", relative))
    for source in targets:
        seen = {source}; current = source
        while current in targets:
            current = targets[current]
            if current in seen:
                errors.append(error("redirect_cycle", source)); break
            seen.add(current)
    return errors


def validate_status(root: Path) -> list[str]:
    errors: list[str] = []
    main = yaml.safe_load((root / "docs/status/project-status.yaml").read_text(encoding="utf-8"))
    lab = yaml.safe_load((root / "docs/status/v0_4_track.yaml").read_text(encoding="utf-8"))
    expected_main = {"current_completed_stage": "v0.3.18", "next_allowed_stage": "v0.3.19", "current_candidate": CANDIDATE_ID, "production_ready": False, "shadow_mode_ready": False, "backend_integration_ready": False}
    expected_lab = {"latest_completed_stage": "v0.4.4", "allowed_next_stage": "v0.4.5", "mainline_next_allowed_stage": "v0.3.19", "candidate_id": CANDIDATE_ID, "production_ready": False, "laboratory_only": True}
    for key, value in expected_main.items():
        if main.get(key) != value: errors.append(error("mainline_status_mismatch", key))
    for key, value in expected_lab.items():
        if lab.get(key) != value: errors.append(error("laboratory_status_mismatch", key))
    required_texts = ("README.md", "docs/status/current-status.md", "docs/status/next-stage.md", "docs/roadmap.md")
    for name in required_texts:
        text = (root / name).read_text(encoding="utf-8")
        for marker in ("v0.3.18", "v0.3.19", "v0.4.4", "v0.4.5"):
            if marker not in text: errors.append(error("status_marker_missing", name, marker))
    registry = json.loads((root / "collectors/shadow/contracts/candidate_registry_v1.json").read_text(encoding="utf-8"))
    if CANDIDATE_ID not in json.dumps(registry, ensure_ascii=False): errors.append("candidate_identity_mismatch")
    if run_git("rev-parse", "HEAD:backend", root=root) != BACKEND_TREE: errors.append("backend_tree_changed")
    return errors


def validate_indexes(root: Path) -> list[str]:
    errors: list[str] = []
    contract_text = (root / "docs/contracts/index.md").read_text(encoding="utf-8")
    schemas = {p.relative_to(root).as_posix() for p in root.rglob("*.schema.json") if "runtime" not in p.parts}
    for path in schemas:
        if path not in contract_text: errors.append(error("contract_index_incomplete", path))
    protocol_text = (root / "docs/protocols/index.md").read_text(encoding="utf-8")
    protocols = {*root.glob("ml/protocols/*.yaml"), *root.glob("incident_reconstruction/protocols/*.yaml")}
    for path in protocols:
        relative = path.relative_to(root).as_posix()
        if relative not in protocol_text: errors.append(error("protocol_index_incomplete", relative))
    report_text = (root / "docs/reports/index.md").read_text(encoding="utf-8")
    for directory in (root / "ml/reports").glob("v0_[34]_*" ):
        stage = directory.name.replace("_", ".")
        if directory.is_dir() and stage not in report_text: errors.append(error("report_index_incomplete", stage))
    return errors


def validate_commands_and_routes(root: Path) -> list[str]:
    errors: list[str] = []
    path = root / "docs/reference/command-reference.md"
    text = path.read_text(encoding="utf-8")
    for module in re.findall(r"python -m ([A-Za-z_][\w.]*)", text):
        if module in {"pip", "pytest", "compileall", "lab_console"}:
            target = root / "lab_console/__main__.py" if module == "lab_console" else None
        else:
            target = root / (module.replace(".", "/") + ".py")
        if target is not None and not target.is_file():
            errors.append(error("command_module_missing", path.relative_to(root).as_posix(), module))
    app_text = (root / "lab_console/app.py").read_text(encoding="utf-8")
    console_docs = (root / "lab_console/README.md").read_text(encoding="utf-8")
    if "/api/console/v1/" not in console_docs or "/api/console/v1" not in app_text:
        errors.append("documented_api_route_missing")
    if "/ui/cases" not in (root / "docs/getting-started/laboratory-console.md").read_text(encoding="utf-8"):
        errors.append("documented_ui_route_missing")
    return errors


def validate_inventory(root: Path, markdown: list[Path]) -> list[str]:
    path = root / "docs/audit/documentation_inventory_v2.json"
    if not path.is_file(): return ["inventory_missing"]
    value = json.loads(path.read_text(encoding="utf-8"))
    recorded = {row["path"] for row in value.get("documents", [])}
    actual = {p.relative_to(root).as_posix() for p in markdown}
    errors = []
    if recorded != actual: errors.append("inventory_stale")
    required = {"path", "title", "category", "audience", "lifecycle_status", "current_or_historical", "authoritative", "generated", "evidence_immutable", "protected_by_manifest", "source_of_truth", "duplicate_of", "supersedes", "superseded_by", "redirect_target", "last_relevant_stage", "current_stage_mentioned", "stale_status", "stale_architecture", "stale_command", "terminology_findings", "broken_links", "broken_anchors", "incoming_link_count", "outgoing_link_count", "recommended_action", "actual_action", "sha256_before", "sha256_after"}
    for row in value.get("documents", []):
        missing = required - set(row)
        if missing: errors.append(error("inventory_fields_missing", row.get("path", "?"), ",".join(sorted(missing))))
        target = root / row.get("path", "")
        if target.is_file() and row.get("path") != "docs/audit/documentation_inventory_v2.md" and row.get("sha256_after") != sha256(target): errors.append(error("inventory_sha_stale", row.get("path", "")))
    return errors


def validate(root: Path = ROOT) -> dict[str, Any]:
    root = root.resolve()
    markdown = tracked_markdown(root)
    protected_rows = build_protected_set(root)
    protected = {row["path"] for row in protected_rows}
    errors: list[str] = []
    warnings: list[str] = []

    for required in REQUIRED_ROOTS:
        if not (root / required).is_dir(): errors.append(error("required_root_missing", required))
    for required in REQUIRED_CURRENT_DOCS:
        if not (root / required).is_file(): errors.append(error("required_document_missing", required))
    for required in REQUIRED_SUBSYSTEM_READMES:
        if not (root / required).is_file(): errors.append(error("subsystem_readme_missing", required))

    incoming: Counter[str] = Counter()
    for path in markdown:
        relative = path.relative_to(root).as_posix()
        errors.extend(validate_headings(path, root))
        broken, anchors, escapes = link_findings(path, root)
        errors.extend(error("broken_link", relative, item) for item in broken)
        errors.extend(error("broken_anchor", relative, item) for item in anchors)
        errors.extend(error("link_escapes_repository", relative, item) for item in escapes)
        errors.extend(validate_mermaid(path, root))
        for _, destination, _ in local_links(path, root):
            if destination and destination.exists():
                try: incoming[destination.relative_to(root).as_posix()] += 1
                except ValueError: pass
        if relative in REQUIRED_CURRENT_DOCS and relative not in protected:
            meta = front_matter(path)
            missing = REQUIRED_FRONT_MATTER - set(meta)
            if missing: errors.append(error("missing_front_matter", relative, ",".join(sorted(missing))))
            if meta.get("doc_schema") != "filin_document_v2": errors.append(error("front_matter_schema", relative))
        if current_mutable(path, protected, root):
            text = path.read_text(encoding="utf-8")
            if ABSOLUTE_RE.search(text): errors.append(error("absolute_local_path", relative))
            for pattern in SECRET_RES:
                if pattern.search(text): errors.append(error("possible_secret", relative))
            lower = text.casefold()
            if re.search(r"\b\d{3,5}\s+passed\b", lower) and not relative.startswith("docs/audit/"):
                errors.append(error("stale_test_count", relative))
            if any(phrase in lower for phrase in ("v0.4.x планируется", "v0.4.x является планируемой архитектурой")):
                errors.append(error("stale_v04_planned_claim", relative))
            if "production_ready: true" in lower or "backend_integration_allowed: true" in lower:
                errors.append(error("prohibited_readiness_claim", relative))

    for relative in REQUIRED_CURRENT_DOCS:
        meta = front_matter(root / relative)
        if meta.get("lifecycle") == "current" and relative not in {"README.md", "docs/index.md"} and incoming[relative] == 0:
            errors.append(error("orphan_current_document", relative))

    authority: defaultdict[str, list[str]] = defaultdict(list)
    for path in markdown:
        relative = path.relative_to(root).as_posix()
        for domain in front_matter(path).get("authoritative_for", []) or []:
            authority[str(domain)].append(relative)
    for domain, paths in authority.items():
        if len(paths) > 1: errors.append(error("duplicate_authoritative_document", domain, ",".join(paths)))

    errors.extend(validate_redirects(markdown, root))
    errors.extend(validate_status(root))
    errors.extend(validate_indexes(root))
    errors.extend(validate_commands_and_routes(root))
    errors.extend(validate_inventory(root, markdown))

    registry_path = root / "docs/audit/protected_documentation_v2.json"
    if not registry_path.is_file(): errors.append("protected_registry_missing")
    else:
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
        recorded = {row["path"]: row for row in registry.get("files", [])}
        if set(recorded) != protected: errors.append("protected_set_stale")
        for relative, row in recorded.items():
            target = root / relative
            if not target.is_file(): errors.append(error("protected_file_missing", relative))
            elif sha256(target) != row.get("actual_sha256"): errors.append(error("protected_file_changed", relative))
            if not row.get("manifest_sha_matches", True): warnings.append(error("baseline_manifest_sha_mismatch", relative))

    readme = (root / "README.md").read_text(encoding="utf-8")
    for marker in ("Основная `v0.3.x`", "Лабораторная `v0.4.x`", CANDIDATE_ID, "docs/index.md"):
        if marker not in readme: errors.append(error("readme_marker_missing", detail=marker))
    if "v0.4.4" not in (root / "docs/getting-started/reviewing-laboratory-cards.md").read_text(encoding="utf-8"):
        errors.append("v044_operator_guide_missing")
    all_current = "\n".join(path.read_text(encoding="utf-8").casefold() for path in markdown if current_mutable(path, protected, root))
    if any(phrase in all_current for phrase in ("v0.4.5 завершён", "v0.4.5 завершен", "v0.4.5 completed", "v0.4.5 уже реализован")): errors.append("v045_false_completion_claim")
    if "v0.3.19" not in all_current: errors.append("v0319_boundary_missing")

    return {"valid": not errors, "checked_markdown": len(markdown), "protected_files": len(protected), "error_count": len(set(errors)), "warning_count": len(set(warnings)), "errors": sorted(set(errors)), "warnings": sorted(set(warnings))}


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--strict", action="store_true"); parser.add_argument("--root", type=Path, default=ROOT); args = parser.parse_args()
    result = validate(args.root)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["valid"] or not args.strict else 1


if __name__ == "__main__":
    raise SystemExit(main())
