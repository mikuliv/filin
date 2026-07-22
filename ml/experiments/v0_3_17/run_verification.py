from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
RUNTIME = ROOT / "runtime/v0_3_17"


def command(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=ROOT, text=True, capture_output=True)


def main() -> int:
    pytest = command([sys.executable, "-m", "pytest", "ml/tests/test_v0317_rehearsal.py", "-q", "--basetemp", "runtime/pytest-v0317-verification"])
    compileall = command([sys.executable, "-m", "compileall", "-q", "rehearsal", "ml/experiments/v0_3_17", "tools/audit"])
    match = __import__("re").search(r"(\d+) passed", pytest.stdout)
    result = {
        "schema_version": "v0317_verification_v1",
        "behavioral_tests_passed": pytest.returncode == 0,
        "test_count": int(match.group(1)) if match else 0,
        "pytest_stdout_tail": pytest.stdout[-1000:],
        "pytest_stderr_tail": pytest.stderr[-1000:],
        "compileall_passed": compileall.returncode == 0,
        "ci_stage_tests_enabled": True,
    }
    RUNTIME.mkdir(parents=True, exist_ok=True)
    (RUNTIME / "verification_result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["behavioral_tests_passed"] and result["compileall_passed"] and result["test_count"] >= 57 else 1


if __name__ == "__main__":
    raise SystemExit(main())
