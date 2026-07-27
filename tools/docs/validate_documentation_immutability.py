"""Проверяет protected set Documentation v2."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from tools.docs.documentation_v2 import ROOT, build_protected_set, sha256


def validate(root: Path = ROOT) -> list[str]:
    registry_path = root / "docs/audit/protected_documentation_v2.json"
    if not registry_path.is_file():
        return ["protected_registry_missing"]
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    errors: list[str] = []
    current = {row["path"]: row for row in build_protected_set(root)}
    recorded = {row["path"]: row for row in registry.get("files", [])}
    if set(current) != set(recorded):
        errors.append("protected_set_stale")
    for path, row in recorded.items():
        target = root / path
        if not target.is_file():
            errors.append(f"protected_file_missing:{path}")
        elif sha256(target) != row.get("actual_sha256"):
            errors.append(f"protected_file_changed:{path}")
        if row.get("mutable") is not False:
            errors.append(f"protected_file_mutable:{path}")
    return sorted(set(errors))


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--root", type=Path, default=ROOT); args = parser.parse_args()
    errors = validate(args.root.resolve())
    print(json.dumps({"valid": not errors, "errors": errors}, ensure_ascii=False, indent=2))
    return int(bool(errors))


if __name__ == "__main__":
    raise SystemExit(main())
