"""Проверяет, что технические идентификаторы не содержат кириллицу."""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.docs.documentation_v2 import ROOT, build_protected_set, document_metadata, tracked_markdown  # noqa: E402


CYRILLIC = re.compile(r"[А-Яа-яЁё]")
ASCII = re.compile(r"[A-Za-z]")
STRUCTURE = re.compile(r"[_./:-]")


@dataclass(frozen=True)
class Finding:
    path: str
    line: int
    literal: str
    message: str = "Технический идентификатор не должен содержать кириллицу."


def _looks_like_identifier(value: str) -> bool:
    return bool(CYRILLIC.search(value) and ASCII.search(value) and STRUCTURE.search(value))


def find_in_text(text: str, path: str = "<fixture>") -> list[Finding]:
    findings: list[Finding] = []
    in_fence = False
    for line_number, line in enumerate(text.splitlines(), 1):
        if re.match(r"^\s*(```|~~~)", line):
            in_fence = not in_fence
            continue
        inline_spans = [match.group(1) for match in re.finditer(r"`([^`\n]+)`", line)]
        spans: list[str] = []
        for literal in inline_spans:
            # Пояснение вроде `<официальный package_id>` не является
            # испорченным идентификатором.
            if _looks_like_identifier(literal) and not re.search(r"[<>\"']", literal):
                spans.append(literal)
            else:
                spans.extend(re.findall(r"[A-Za-zА-Яа-яЁё0-9_./:-]+", literal))
        if in_fence:
            spans.extend(re.findall(r"[A-Za-zА-Яа-яЁё0-9_./:-]+", line))
        for literal in spans:
            if _looks_like_identifier(literal):
                findings.append(Finding(path, line_number, literal))
    return findings


def validate(root: Path = ROOT) -> list[Finding]:
    protected = {row["path"] for row in build_protected_set(root)}
    findings: list[Finding] = []
    for path in tracked_markdown(root):
        relative = path.relative_to(root).as_posix()
        if relative in protected or document_metadata(path, root).get("lifecycle") in {"historical", "frozen", "generated"}:
            continue
        findings.extend(find_in_text(path.read_text(encoding="utf-8"), relative))
    return findings


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    findings = validate(args.root.resolve())
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps({"valid": not findings, "finding_count": len(findings), "findings": [asdict(item) for item in findings]}, ensure_ascii=False, indent=2))
    return 1 if args.strict and findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
