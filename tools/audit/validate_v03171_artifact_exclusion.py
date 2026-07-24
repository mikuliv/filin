from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
FORBIDDEN_SUFFIXES = {
    ".pcap",
    ".pcapng",
    ".sqlite",
    ".db",
    ".key",
    ".pem",
    ".joblib",
    ".pkl",
}
FORBIDDEN_PARTS = {
    "__pycache__",
    "operator_snapshots",
    "raw_timing_traces",
    "storage_snapshots",
}


def validate() -> dict:
    tracked = subprocess.check_output(
        ["git", "ls-files"], cwd=ROOT, text=True, encoding="utf-8"
    ).splitlines()
    violations: list[str] = []
    local_path_findings: list[str] = []
    for relative in tracked:
        normalized = relative.replace("\\", "/")
        path = Path(normalized)
        if (
            normalized.startswith("runtime/")
            or path.suffix.lower() in FORBIDDEN_SUFFIXES
            or FORBIDDEN_PARTS.intersection(path.parts)
        ):
            if normalized in {"runtime/.env.example", "runtime/docker-compose.demo.yml"}:
                continue
            if normalized.startswith("ml/reports/"):
                continue
            violations.append(normalized)
        if normalized.startswith(
            (
                "ml/reports/v0_3_17_1/",
                "ml/protocols/v0_3_17_1",
                "docs/experiments/v0_3_17_1",
            )
        ):
            target = ROOT / relative
            if target.is_file():
                text = target.read_text(encoding="utf-8")
                if re.search(r"\b[A-Za-z]:[\\/]", text):
                    local_path_findings.append(normalized)
    return {
        "passed": not violations and not local_path_findings,
        "tracked_file_count": len(tracked),
        "artifact_violations": sorted(violations),
        "absolute_local_path_findings": sorted(local_path_findings),
    }


def main() -> int:
    result = validate()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
