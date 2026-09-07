"""Проверяет локальные Markdown-ссылки, якоря и выход за пределы репозитория."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.docs.documentation_v2 import ROOT, link_findings, tracked_markdown  # noqa: E402


def validate(root: Path = ROOT) -> dict:
    findings = []
    for path in tracked_markdown(root):
        broken, anchors, escapes = link_findings(path, root)
        relative = path.relative_to(root).as_posix()
        findings.extend({"path": relative, "kind": kind, "link": link} for kind, links in (
            ("broken", broken), ("missing_anchor", anchors), ("repository_escape", escapes)
        ) for link in links)
    return {
        "schema_version": "filin_documentation_link_validation_v1",
        "valid": not findings,
        "checked_markdown": len(tracked_markdown(root)),
        "finding_count": len(findings),
        "findings": findings,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    result = validate(args.root.resolve())
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if args.strict and not result["valid"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
