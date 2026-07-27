"""Проверяет актуальность inventory и stage markers."""
from __future__ import annotations

import json

from tools.docs.documentation_v2 import ROOT, tracked_markdown


def validate() -> list[str]:
    path=ROOT/"docs/audit/documentation_inventory_v2.json"
    if not path.is_file(): return ["inventory_missing"]
    data=json.loads(path.read_text(encoding="utf-8")); recorded={x["path"] for x in data.get("documents",[])}
    actual={p.relative_to(ROOT).as_posix() for p in tracked_markdown(ROOT)}
    errors=[]
    if recorded!=actual: errors.append("inventory_stale")
    for name in ("README.md","docs/status/current-status.md","docs/architecture/overview.md"):
        text=(ROOT/name).read_text(encoding="utf-8")
        if "v0.4.4" not in text: errors.append(f"current_stage_missing:{name}")
    return errors


def main() -> int:
    errors=validate(); print(json.dumps({"valid":not errors,"errors":errors},ensure_ascii=False,indent=2)); return int(bool(errors))


if __name__ == "__main__": raise SystemExit(main())
