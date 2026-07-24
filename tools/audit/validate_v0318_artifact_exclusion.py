"""Проверка tracked artifacts и локальных путей v0.3.18."""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
FORBIDDEN_SUFFIXES = {
    ".pcap", ".pcapng", ".joblib", ".sqlite", ".db", ".wal", ".key",
    ".pem", ".pfx", ".zip", ".7z", ".tar", ".gz",
}
WINDOWS_PATH = re.compile(r"(?i)\b[A-Z]:[\\/]")


def validate() -> dict:
    tracked = subprocess.check_output(["git", "ls-files"], cwd=ROOT, text=True).splitlines()
    violations: list[str] = []
    absolute: list[str] = []
    for relative in tracked:
        path = ROOT / relative
        if path.suffix.lower() in FORBIDDEN_SUFFIXES and (
            relative.startswith("ml/reports/v0_3_18/")
            or relative.startswith("external_review/")
        ):
            violations.append(relative)
        if not path.is_file() or path.stat().st_size > 2 * 1024 * 1024:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if relative.startswith(("ml/reports/v0_3_18/", "docs/external_review/", "external_review/contracts/")):
            if WINDOWS_PATH.search(text) or "/home/" in text:
                absolute.append(relative)
    return {
        "schema_version": "v0318_artifact_exclusion_report_v1",
        "artifact_exclusion_passed": not violations and not absolute,
        "tracked_file_count": len(tracked),
        "forbidden_artifacts": violations,
        "absolute_local_path_findings": absolute,
    }


def main() -> int:
    result = validate()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["artifact_exclusion_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
