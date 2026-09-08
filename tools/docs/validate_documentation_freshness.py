"""Проверяет актуальность документации относительно последнего пакета Phase 1."""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.docs.documentation_v2 import (  # noqa: E402
    ROOT,
    build_protected_set,
    document_metadata,
    phase1_facts,
    tracked_markdown,
)
from tools.docs.validate_documentation_v2 import validate_inventory  # noqa: E402


CURRENT_PAGES = (
    "README.md",
    "docs/index.md",
    "docs/status/current-status.md",
    "docs/architecture/overview.md",
    "docs/research/independent-network-validation.md",
)


def stale_findings(text: str, facts: dict) -> list[str]:
    """Ищет устаревшее состояние относительно фактического плана."""
    expected_count = int(facts["scenario_template_count"])
    findings: list[str] = []
    for match in re.finditer(r"(?<!по )\b(\d+)\s+(?:сценар(?:иев|ия|иям|ий)|шаблон(?:ов|а)?|(?:scenario\s+)?templates?)\b", text, flags=re.IGNORECASE):
        if int(match.group(1)) != expected_count:
            findings.append("stale_phase1_scenario_count")
    if re.search(r"\bfuture\s+independent\s+network\s+validation\b", text, flags=re.IGNORECASE):
        findings.append("stale_future_protocol_claim")
    if re.search(r"\bscientific_campaign_started\s*[:=]\s*true\b", text, flags=re.IGNORECASE):
        findings.append("unqualified_started_claim")
    return sorted(set(findings))


def validate(root: Path = ROOT) -> list[str]:
    inventory_path = root / "docs/audit/documentation_inventory_v2.json"
    if not inventory_path.is_file():
        return ["inventory_missing"]
    data = json.loads(inventory_path.read_text(encoding="utf-8"))
    recorded = {row["path"] for row in data.get("documents", []) if isinstance(row, dict) and "path" in row}
    markdown = tracked_markdown(root)
    actual = {path.relative_to(root).as_posix() for path in markdown}
    errors: list[str] = []
    if recorded != actual:
        errors.append("inventory_stale")
    errors.extend(validate_inventory(root, markdown))

    facts = phase1_facts(root)
    required_markers = (
        facts["package_id"],
        str(facts["scenario_template_count"]),
        str(facts["execution_unit_count"]),
        str(facts["feature_count"]),
    )
    protected = {row["path"] for row in build_protected_set(root)}
    for relative in CURRENT_PAGES:
        path = root / relative
        if not path.is_file():
            errors.append(f"current_page_missing:{relative}")
            continue
        text = path.read_text(encoding="utf-8")
        for marker in required_markers:
            if marker not in text:
                errors.append(f"current_marker_missing:{relative}:{marker}")

    for path in markdown:
        relative = path.relative_to(root).as_posix()
        if relative in protected:
            continue
        metadata = document_metadata(path, root)
        if metadata.get("lifecycle") not in {"current", "generated", "redirect"} and not relative.endswith("README.md"):
            continue
        text = path.read_text(encoding="utf-8")
        errors.extend(f"{code}:{relative}" for code in stale_findings(text, facts))
    return sorted(set(errors))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--strict", action="store_true")
    parser.parse_args()
    errors = validate()
    print(json.dumps({"valid": not errors, "errors": errors}, ensure_ascii=False, indent=2))
    return int(bool(errors))


if __name__ == "__main__":
    raise SystemExit(main())
