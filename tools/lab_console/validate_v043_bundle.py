from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "ml/reports/v0_4_3"


def main() -> int:
    manifest = json.loads((OUT / "v0_4_3_bundle_manifest.json").read_text(encoding="utf-8"))
    errors = []
    for item in manifest["artifacts"]:
        path = ROOT / item["path"]
        if not path.exists(): errors.append(f"missing:{item['path']}"); continue
        data = path.read_bytes().replace(b"\r\n", b"\n")
        if hashlib.sha256(data).hexdigest() != item["sha256"]: errors.append(f"hash:{item['path']}")
    print(json.dumps({"schema_version": "v0_4_3_bundle_validation_v1", "artifact_count": manifest["artifact_count"], "errors": errors, "passed": not errors}, ensure_ascii=False))
    return 1 if errors else 0


if __name__ == "__main__": raise SystemExit(main())
