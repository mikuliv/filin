from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
REQUIRED = [
    ROOT / "docs/experiments/v0_3_17.md",
    ROOT / "docs/architecture/controlled_local_rehearsal_v0_3_17.md",
    ROOT / "docs/contracts/operator_projection_v1.md",
    ROOT / "docs/contracts/rehearsal_observability_v1.md",
    ROOT / "docs/operations/local_rehearsal_runbook.md",
    ROOT / "docs/operations/local_rehearsal_recovery_runbook.md",
]


def main() -> int:
    errors = []
    for path in REQUIRED:
        if not path.is_file():
            errors.append(f"missing:{path.relative_to(ROOT)}")
    text = "\n".join(path.read_text(encoding="utf-8") for path in REQUIRED if path.is_file()).lower()
    for required in ("не реальный shadow mode", "backend integration", "production", "design-review", "read-only"):
        if required.lower() not in text:
            errors.append(f"semantic_missing:{required}")
    forbidden_patterns = [r"production[_ ]ready\s*[=:]\s*true", r"shadow[_ ]mode[_ ]allowed\s*[=:]\s*true", r"backend[_ ]integration[_ ]allowed\s*[=:]\s*true"]
    for pattern in forbidden_patterns:
        if re.search(pattern, text):
            errors.append(f"forbidden_claim:{pattern}")
    print(json.dumps({"passed": not errors, "errors": errors, "document_count": len(REQUIRED)}, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())

