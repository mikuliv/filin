"""Выгрузка frozen JSON Schemas этапа v0.3.18."""
from __future__ import annotations

import json
from pathlib import Path

from ml.experiments.v0_3_18.contracts import SCHEMAS


ROOT = Path(__file__).resolve().parents[3]
TARGET = ROOT / "external_review/contracts"


def main() -> int:
    TARGET.mkdir(parents=True, exist_ok=True)
    for name, schema in sorted(SCHEMAS.items()):
        (TARGET / f"{name}.schema.json").write_text(
            json.dumps(schema, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
            newline="\n",
        )
    print(json.dumps({"schema_count": len(SCHEMAS), "target": "external_review/contracts"}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
