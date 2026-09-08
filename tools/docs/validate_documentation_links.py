"""Проверяет локальные Markdown-ссылки, якоря и выход за пределы репозитория."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.docs.documentation_v2 import ROOT, portable_link_audit, tracked_markdown  # noqa: E402


def validate(root: Path = ROOT) -> dict:
    findings = []
    counts = {"tracked": 0, "generated": 0, "local_only": 0, "broken": 0, "missing_anchor": 0, "repository_escape": 0}
    markdown = tracked_markdown(root, include_untracked=False)
    for path in markdown:
        relative = path.relative_to(root).as_posix()
        for row in portable_link_audit(path, root):
            counts[row["kind"]] += 1
            if row["kind"] not in {"tracked", "generated"}:
                findings.append({"path": relative, **row})
    return {
        "schema_version": "filin_documentation_link_validation_v2",
        "valid": not findings,
        "repository_portable": not findings,
        "checked_markdown": len(markdown),
        "tracked_link_count": counts["tracked"],
        "generated_link_count": counts["generated"],
        "local_only_link_count": counts["local_only"],
        "broken_link_count": counts["broken"],
        "broken_anchor_count": counts["missing_anchor"],
        "repository_escape_count": counts["repository_escape"],
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
