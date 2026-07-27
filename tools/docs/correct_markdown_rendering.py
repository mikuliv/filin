"""Удаляет видимый YAML front matter, сохраняя metadata в inventory v2."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from tools.docs.documentation_v2 import ROOT, build_protected_set, inventory_registry, tracked_markdown


def strip_front_matter(text: str) -> tuple[str, bool]:
    if not text.startswith("---\n"):
        return text, False
    end = text.find("\n---\n", 4)
    if end < 0:
        return text, False
    return text[end + 5 :].lstrip("\n"), True


def correct(root: Path = ROOT) -> dict[str, object]:
    root = root.resolve()
    metadata = inventory_registry(root)
    protected = {row["path"] for row in build_protected_set(root)}
    found: list[str] = []
    corrected: list[str] = []
    skipped_protected: list[str] = []
    for path in tracked_markdown(root):
        relative = path.relative_to(root).as_posix()
        original = path.read_text(encoding="utf-8")
        updated, has_front_matter = strip_front_matter(original)
        if not has_front_matter:
            continue
        found.append(relative)
        if relative in protected:
            skipped_protected.append(relative)
            continue
        if relative not in metadata:
            raise RuntimeError(f"metadata отсутствует в inventory: {relative}")
        if not updated.startswith("# "):
            raise RuntimeError(f"после удаления metadata первым элементом не является H1: {relative}")
        path.write_text(updated, encoding="utf-8", newline="\n")
        corrected.append(relative)
    return {
        "found_count": len(found),
        "corrected_count": len(corrected),
        "protected_skipped_count": len(skipped_protected),
        "found": found,
        "corrected": corrected,
        "protected_skipped": skipped_protected,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    print(json.dumps(correct(args.root), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
