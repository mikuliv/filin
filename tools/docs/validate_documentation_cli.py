"""Проверяет CLI-команды, упомянутые в текущей документации."""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from lab.network_validation.cli import parser as build_parser  # noqa: E402
from tools.docs.documentation_v2 import ROOT, build_protected_set, document_metadata, tracked_markdown  # noqa: E402


COMMAND_RE = re.compile(r"python -m lab\.network_validation\.cli\s+([a-z][a-z0-9-]+)")
TABLE_COMMAND_RE = re.compile(r"^\|\s*`((?:validate|inspect|audit|build|create|materialize|verify|plan|render|run|recover|preflight|definitely)-[a-z0-9-]+)`\s*\|", re.MULTILINE)


def available_commands() -> set[str]:
    action = next(item for item in build_parser()._actions if item.dest == "command")
    return set(action.choices)


def find_unknown_commands(text: str, available: set[str] | None = None) -> list[str]:
    available = available_commands() if available is None else available
    references = COMMAND_RE.findall(text) + TABLE_COMMAND_RE.findall(text)
    return sorted({command for command in references if command not in available})


def validate(root: Path = ROOT) -> list[dict[str, str]]:
    protected = {row["path"] for row in build_protected_set(root)}
    findings: list[dict[str, str]] = []
    for path in tracked_markdown(root):
        relative = path.relative_to(root).as_posix()
        if relative in protected or document_metadata(path, root).get("lifecycle") in {"historical", "frozen", "generated"}:
            continue
        for command in find_unknown_commands(path.read_text(encoding="utf-8")):
            findings.append({"path": relative, "command": command})
    return findings


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    findings = validate(args.root.resolve())
    print(json.dumps({"valid": not findings, "available_command_count": len(available_commands()), "finding_count": len(findings), "findings": findings}, ensure_ascii=False, indent=2))
    return 1 if args.strict and findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
