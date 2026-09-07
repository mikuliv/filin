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

    stale_patterns = (
        (r"\b72\s+(?:сценар(?:ий|ия|иям|иев)|шаблон(?:ов|а)?)\b", "stale_72_scenario_claim"),
        (r"\bfuture\s+independent\s+network\s+validation\b", "stale_future_protocol_claim"),
        (r"\bscientific_campaign_started\s*[:=]\s*true\b", "unqualified_started_claim"),
    )
    for path in markdown:
        relative = path.relative_to(root).as_posix()
        if relative in protected:
            continue
        metadata = document_metadata(path, root)
        if metadata.get("lifecycle") not in {"current", "generated", "redirect"} and not relative.endswith("README.md"):
            continue
        text = path.read_text(encoding="utf-8")
        for pattern, code in stale_patterns:
            if re.search(pattern, text, flags=re.IGNORECASE):
                errors.append(f"{code}:{relative}")
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
