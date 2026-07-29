"""Удаляет ошибочное кодовое оформление только внутри адресов Markdown-ссылок."""
from __future__ import annotations

import re

from tools.docs.validate_russian_narrative import ROOT, tracked_paths


def repair(text: str) -> str:
    def clean(match: re.Match[str]) -> str:
        label, destination = match.group(1), match.group(2)
        return f"[{label}]({destination.replace('`', '')})"
    return re.sub(r"\[([^\]]+)\]\(([^)]+)\)", clean, text)


def main() -> int:
    changed = []
    for path in tracked_paths(ROOT):
        target = ROOT / path
        if target.suffix.lower() != ".md" or not target.is_file():
            continue
        try:
            text = target.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        updated = repair(text)
        if updated != text:
            target.write_text(updated, encoding="utf-8", newline="")
            changed.append(path)
    print(f"Исправлено адресов в файлах: {len(changed)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
