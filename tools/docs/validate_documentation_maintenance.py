"""Строгая локальная проверка документации после v0.3.18."""
from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path
from urllib.parse import unquote

import yaml


ROOT = Path(__file__).resolve().parents[2]
BASELINE_HEAD = "c81873c72a0586bb81ba72bd035d67f75e7a20a5"
CURRENT_SECTIONS = (
    "getting-started",
    "architecture",
    "research",
    "status",
    "contributing",
)
INDEXED_CURRENT_EXCEPTIONS = {
    "docs/status/project-status.yaml",
    "docs/status/v0_3_18_working_handoff.md",
    "docs/status/documentation_refactor_handoff.md",
    "docs/architecture/controlled_local_rehearsal_v0_3_17.md",
    "docs/architecture/staging_connector_v0_3_16.md",
}
PROTECTED_PATHS = (
    "external_review/contracts",
    "collectors/shadow/contracts",
    "ml/artifacts/v0_3_15_4",
    "ml/protocols",
    "ml/reports/v0_3_17",
    "ml/reports/v0_3_17_1",
    "ml/reports/v0_3_18",
)
REQUIRED_INDEX_LINKS = (
    "getting-started/overview.md",
    "architecture/overview.md",
    "research/methodology.md",
    "status/current-status.md",
    "status/confirmed-capabilities.md",
    "status/prohibited-capabilities.md",
    "status/version-history.md",
    "external_review/README.md",
    "contracts/index.md",
    "protocols/index.md",
    "reports/index.md",
    "history/stage-timeline.md",
    "contributing/documentation-style.md",
    "audit/documentation_inventory.md",
)
FORBIDDEN_ABSOLUTE = re.compile(
    r"(?i)(?:[A-Z]:[\\/](?:Users|Filin|Projects|Anomalyzer)|/home/[^/\s]+/|/Users/[^/\s]+/)"
)
SECRET_PATTERNS = (
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(r"(?i)\b(?:api[_-]?key|secret|token|password)\s*[:=]\s*['\"][^'\"]{8,}['\"]"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}\b"),
)
LINK = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")
HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*$", re.MULTILINE)


def tracked_markdown(root: Path = ROOT) -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", "*.md"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return [root / line for line in result.stdout.splitlines() if line]


def slug(value: str) -> str:
    value = re.sub(r"[^\w\s-]", "", value.casefold(), flags=re.UNICODE)
    return re.sub(r"[\s_-]+", "-", value).strip("-")


def front_matter(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return {}
    end = text.find("\n---\n", 4)
    if end < 0:
        return {}
    return yaml.safe_load(text[4:end]) or {}


def validate_links(path: Path, root: Path) -> list[str]:
    errors: list[str] = []
    text = path.read_text(encoding="utf-8")
    for raw in LINK.findall(text):
        target = raw.strip().strip("<>")
        if not target or target.startswith(("http://", "https://", "mailto:")):
            continue
        file_part, _, anchor = unquote(target).partition("#")
        destination = path if not file_part else (path.parent / file_part).resolve()
        try:
            destination.relative_to(root.resolve())
        except ValueError:
            errors.append(f"link_escapes_repository:{path.relative_to(root)}:{raw}")
            continue
        if not destination.exists():
            errors.append(f"broken_link:{path.relative_to(root)}:{raw}")
            continue
        if anchor and destination.suffix.casefold() == ".md":
            headings = {
                slug(title)
                for _, title in HEADING.findall(destination.read_text(encoding="utf-8"))
            }
            if anchor.casefold() not in headings:
                errors.append(f"broken_anchor:{path.relative_to(root)}:{raw}")
    return errors


def validate_headings(path: Path, root: Path) -> list[str]:
    headings = [(len(marks), title.strip()) for marks, title in HEADING.findall(path.read_text(encoding="utf-8"))]
    relative = path.relative_to(root)
    errors: list[str] = []
    h1 = [title for level, title in headings if level == 1]
    if len(h1) != 1:
        errors.append(f"h1_count:{relative}:{len(h1)}")
    for previous, current in zip(headings, headings[1:]):
        if current[0] > previous[0] + 1:
            errors.append(f"heading_jump:{relative}:{previous[0]}->{current[0]}")
    return errors


def validate_status(root: Path) -> list[str]:
    errors: list[str] = []
    status = yaml.safe_load((root / "docs/status/project-status.yaml").read_text(encoding="utf-8")) or {}
    current = front_matter(root / "docs/status/current-status.md")
    policy = json.loads((root / "ml/reports/v0_3_18/v0_3_18_policy_result.json").read_text(encoding="utf-8"))
    expected_current = {
        "latest_completed_stage": "v0.3.18",
        "latest_stage_status": "completed",
        "latest_stage_result": "passed",
        "next_allowed_stage": "v0.3.19",
        "next_stage_scope": "external_package_review_only",
        "external_trial_execution_allowed": False,
        "shadow_mode_allowed": False,
        "backend_integration_allowed": False,
        "production_ready": False,
        "automatic_enforcement_ready": False,
        "real_external_data_used_in_v0_3_18": False,
        "synthetic_rehearsal_scientific_evidence": False,
    }
    for key, value in expected_current.items():
        if current.get(key) != value:
            errors.append(f"current_status_mismatch:{key}")
    expected_project = {
        "current_completed_stage": "v0.3.18",
        "next_allowed_stage": "v0.3.19",
        "candidate_ready_for_v0_3_19_external_package_review": True,
        "external_validation_completed": False,
        "shadow_mode_ready": False,
        "backend_integration_ready": False,
        "production_ready": False,
        "automatic_enforcement_ready": False,
    }
    for key, value in expected_project.items():
        if status.get(key) != value:
            errors.append(f"project_status_mismatch:{key}")
    expected_policy = {
        "stage": "v0.3.18",
        "stage_status": "completed",
        "v0318_stage_passed": True,
        "real_external_data_used": False,
        "real_labels_used": False,
        "real_organization_involved": False,
        "synthetic_rehearsal_scientific_evidence": False,
        "external_trial_execution_allowed": False,
        "backend_integration_allowed": False,
        "shadow_mode_allowed": False,
        "production_ready": False,
    }
    for key, value in expected_policy.items():
        if policy.get(key) != value:
            errors.append(f"v0318_policy_mismatch:{key}")
    return errors


def validate_inventory(root: Path) -> list[str]:
    path = root / "docs/audit/documentation_inventory.md"
    text = path.read_text(encoding="utf-8")
    required = (
        "path",
        "category",
        "audience",
        "current_or_historical",
        "authoritative",
        "evidence_immutable",
        "duplicate_of",
        "outdated",
        "broken_links",
        "recommended_action",
    )
    return [f"inventory_schema_missing:{field}" for field in required if field not in text]


def validate_immutability(root: Path) -> list[str]:
    probe = subprocess.run(
        ["git", "cat-file", "-e", f"{BASELINE_HEAD}^{{commit}}"],
        cwd=root,
        capture_output=True,
    )
    if probe.returncode:
        return ["immutability_baseline_missing"]
    changed = subprocess.run(
        ["git", "diff", "--name-only", BASELINE_HEAD, "--", *PROTECTED_PATHS],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    ).stdout.splitlines()
    return [f"immutable_evidence_changed:{path}" for path in changed]


def validate(root: Path = ROOT) -> dict:
    errors: list[str] = []
    markdown = tracked_markdown(root)
    for path in markdown:
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        errors.extend(validate_links(path, root))
        errors.extend(validate_headings(path, root))
        if FORBIDDEN_ABSOLUTE.search(text):
            errors.append(f"absolute_local_path:{path.relative_to(root)}")
        for pattern in SECRET_PATTERNS:
            if pattern.search(text):
                errors.append(f"possible_secret:{path.relative_to(root)}")

    readme = (root / "README.md").read_text(encoding="utf-8")
    index = (root / "docs/index.md").read_text(encoding="utf-8")
    if "docs/index.md" not in readme:
        errors.append("readme_missing_docs_index")
    for target in REQUIRED_INDEX_LINKS:
        if target not in index:
            errors.append(f"docs_index_missing:{target}")

    for section in CURRENT_SECTIONS:
        for path in sorted((root / "docs" / section).glob("*.md")):
            relative = path.relative_to(root).as_posix()
            if relative not in INDEXED_CURRENT_EXCEPTIONS and path.name not in index:
                errors.append(f"orphan_current_document:{relative}")

    redirect_targets: dict[str, str] = {}
    for path in markdown:
        text = path.read_text(encoding="utf-8")
        if "перенесено" in text.casefold() and len(text.splitlines()) <= 20:
            targets = [raw for raw in LINK.findall(text) if not raw.startswith(("http://", "https://", "#"))]
            if targets:
                redirect_targets[path.resolve().as_posix()] = (path.parent / targets[0].split("#", 1)[0]).resolve().as_posix()
    for source, target in redirect_targets.items():
        if redirect_targets.get(target) == source:
            errors.append(f"cyclic_redirect:{Path(source).relative_to(root)}")

    authoritative_front_matters = [
        path.relative_to(root).as_posix()
        for path in markdown
        if front_matter(path).get("authoritative_status") is True
    ]
    if authoritative_front_matters:
        errors.append("duplicate_authoritative_status:" + ",".join(authoritative_front_matters))

    errors.extend(validate_status(root))
    errors.extend(validate_inventory(root))
    errors.extend(validate_immutability(root))
    return {
        "valid": not errors,
        "checked_markdown": len(markdown),
        "error_count": len(errors),
        "errors": sorted(set(errors)),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()
    result = validate()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["valid"] or not args.strict else 1


if __name__ == "__main__":
    raise SystemExit(main())
