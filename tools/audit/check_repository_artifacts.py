"""Fail CI if generated or protected artifacts become tracked."""
from __future__ import annotations

import subprocess
from pathlib import PurePosixPath


PROTECTED_SUFFIXES = {".pcap", ".pcapng", ".joblib", ".pkl", ".pickle", ".onnx"}
PROTECTED_PREFIXES = ("lab/output/", "ml/artifacts/")
TRACKED_MODEL_METADATA = {"ml/artifacts/v0_3_15_4/candidate_manifest.json"}
TRACKED_RUNTIME_ALLOWLIST = {"runtime/.env.example", "runtime/docker-compose.demo.yml"}
GENERATED_PARTS = {"__pycache__", ".pytest_cache", ".mypy_cache"}


def violations(paths: list[str]) -> list[str]:
    result = []
    for raw in paths:
        path = PurePosixPath(raw.replace("\\", "/")); normalized = path.as_posix()
        runtime_artifact = normalized.startswith("runtime/") and normalized not in TRACKED_RUNTIME_ALLOWLIST
        protected_prefix = normalized.startswith(PROTECTED_PREFIXES) and normalized not in TRACKED_MODEL_METADATA
        if path.suffix.casefold() in PROTECTED_SUFFIXES or protected_prefix or runtime_artifact or GENERATED_PARTS & set(path.parts):
            result.append(normalized)
    return sorted(result)


def main() -> int:
    completed = subprocess.run(["git", "ls-files"], check=True, capture_output=True, text=True, encoding="utf-8")
    bad = violations(completed.stdout.splitlines())
    if bad:
        print("Tracked protected/generated artifacts detected:")
        for path in bad: print(f"- {path}")
        return 1
    print("Protected/generated artifact exclusion passed."); return 0


if __name__ == "__main__": raise SystemExit(main())
