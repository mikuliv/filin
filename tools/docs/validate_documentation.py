"""Проверка структуры документации и единого реестра статуса."""
from __future__ import annotations

import argparse
import re
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]
REQUIRED = (
    "index.md", "architecture.md", "current-capabilities.md", "development-history.md", "experiments.md",
    "data-provenance.md", "reproducibility.md", "safety-model.md", "limitations.md", "glossary.md",
    "status.md", "roadmap.md", "documentation-policy.md", "research-state.yaml", "status/project-status.yaml",
)
ROOT_DIRECTORIES = ("backend", "collectors", "datasets", "docs", "examples", "lab", "ml", "runtime", "tools")
LINK = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")
HEADER = re.compile(r"^#{1,6}\s+(.+?)\s*$", re.MULTILINE)
FORBIDDEN = ("готово к внедрению", "готовая система защиты информации", "сертифицированное средство защиты")


def markdown_files(root: Path) -> list[Path]:
    return sorted(root.rglob("*.md"))


def validate(root: Path = ROOT) -> list[str]:
    errors = []; docs = root / "docs"
    for name in ROOT_DIRECTORIES:
        if not (root / name).is_dir(): errors.append(f"missing required root directory: {name}")
    if (root / "filin").exists(): errors.append("obsolete nested filin directory exists")
    for name in REQUIRED:
        if not (docs / name).is_file(): errors.append(f"missing required document: docs/{name}")
    readme = root / "README.md"
    if not readme.is_file() or "docs/index.md" not in readme.read_text(encoding="utf-8"):
        errors.append("README does not link to docs/index.md")
    for document in markdown_files(root):
        text = document.read_text(encoding="utf-8")
        headings = [heading.strip().casefold() for heading in HEADER.findall(text)]
        duplicates = sorted({heading for heading in headings if headings.count(heading) > 1})
        if duplicates: errors.append(f"duplicate headings in {document.relative_to(root)}: {', '.join(duplicates)}")
        lower = text.casefold()
        for phrase in FORBIDDEN:
            if phrase in lower: errors.append(f"unqualified readiness claim in {document.relative_to(root)}: {phrase}")
        for raw_target in LINK.findall(text):
            target = raw_target.strip()
            if not target or target.startswith(("http://", "https://", "mailto:", "#")): continue
            target = target.split("#", 1)[0]
            if target and not (document.parent / target).resolve().exists(): errors.append(f"broken relative link in {document.relative_to(root)}: {raw_target}")
    try:
        state = yaml.safe_load((docs / "status/project-status.yaml").read_text(encoding="utf-8")) or {}
        legacy = yaml.safe_load((docs / "research-state.yaml").read_text(encoding="utf-8")) or {}
    except Exception as error:
        errors.append(f"status registry cannot be parsed: {type(error).__name__}"); return errors
    required_state = {"current_completed_stage", "next_allowed_stage", "backend_integration_ready", "shadow_mode_ready", "production_ready", "stages"}
    missing = sorted(required_state - set(state))
    if missing: errors.append("project-status.yaml missing keys: " + ", ".join(missing))
    if any(state.get(key) is not False for key in ("backend_integration_ready", "shadow_mode_ready", "production_ready")):
        errors.append("project-status.yaml illegally authorizes integration, shadow mode, or production")
    if legacy.get("deprecated") is not True or legacy.get("authoritative_source") != "status/project-status.yaml":
        errors.append("research-state.yaml is not an explicit compatibility pointer")
    latest = str(state.get("current_completed_stage", ""))
    critical = {
        "README latest stage": (readme, f"Последний завершённый этап: **{latest}**"),
        "status latest stage": (docs / "status.md", f"Текущий завершённый этап: {latest}"),
        "README integration false": (readme, "Backend integration и production connections запрещены"),
        "status production false": (docs / "status.md", "Production, shadow mode, backend integration и automatic enforcement: запрещены"),
        "roadmap completed v0.3.7": (docs / "roadmap.md", "v0.3.7"),
    }
    for label, (path, marker) in critical.items():
        if marker not in path.read_text(encoding="utf-8"): errors.append(f"{label} contradicts project-status.yaml")
    for name in ("current-capabilities.md", "roadmap.md", "experiments.md", "development-history.md"):
        if latest not in (docs / name).read_text(encoding="utf-8"): errors.append(f"docs/{name} does not contain latest completed stage {latest}")
    all_text = "\n".join(path.read_text(encoding="utf-8").casefold() for path in markdown_files(root))
    for claim in ("v0.3.3 is the latest completed experiment", "v0.3.7 policy passed", "backend integration allowed: true", "shadow mode allowed: true", "corrected duration was used in v0.3.7", "v0.3.7 environment profiles were applied", "historical hashes are complete integrity proof"):
        if claim in all_text: errors.append(f"forbidden historical/readiness claim: {claim}")
    if "sensor_ready_for_backend_integration=true" in all_text: errors.append("documentation enables backend integration")
    if "production_ready: true" in all_text or "production ready: true" in all_text: errors.append("documentation claims production readiness")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--strict", action="store_true"); args = parser.parse_args()
    errors = validate()
    if errors:
        print("Documentation validation errors:")
        for error in errors: print(f"- {error}")
        return 1 if args.strict else 0
    print("Documentation validation passed."); return 0


if __name__ == "__main__": raise SystemExit(main())
