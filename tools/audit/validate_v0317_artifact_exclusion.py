from __future__ import annotations

import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
FORBIDDEN_SUFFIXES = {".pcap", ".pcapng", ".sqlite", ".db", ".key", ".pem", ".joblib"}
FORBIDDEN_PARTS = {"runtime/v0_3_17", "operator_snapshots", "resource_samples", "latency_traces"}


def main() -> int:
    tracked = subprocess.check_output(["git", "ls-files"], cwd=ROOT, text=True).splitlines()
    violations = []
    for relative in tracked:
        normalized = relative.replace("\\", "/")
        if normalized.startswith("runtime/v0_3_17/") or Path(normalized).suffix.lower() in FORBIDDEN_SUFFIXES:
            if normalized.startswith("ml/reports/"):
                continue
            violations.append(normalized)
    print(json.dumps({"passed": not violations, "tracked_file_count": len(tracked), "violations": violations}, ensure_ascii=False, indent=2))
    return 0 if not violations else 1


if __name__ == "__main__":
    raise SystemExit(main())
