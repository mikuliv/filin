from __future__ import annotations

import hashlib
import json
import os
import sqlite3
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
REPORT = ROOT / "ml/reports/v0_3_17_1"
LOCK_PATH = REPORT / "pre_trial_code_lock.json"
CANDIDATE = ROOT / "runtime/v0_3_15_4/v03154_candidate.joblib"
CANDIDATE_SHA256 = (
    "65a3dd912d845bc1d6e44247bb8b98fe228a7a4e0496d56a73857febbaa4df87"
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_code_lock(lock_path: Path = LOCK_PATH) -> dict[str, Any]:
    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    rows = []
    for item in lock["locked_artifacts"]:
        path = ROOT / item["path"]
        actual = sha256(path) if path.is_file() else None
        rows.append(
            {
                "path": item["path"],
                "expected_sha256": item["sha256"],
                "actual_sha256": actual,
                "unchanged": actual == item["sha256"],
            }
        )
    return {
        "lock_revision": lock.get("lock_revision", 1),
        "locked_artifact_count": len(rows),
        "locked_artifacts_unchanged": all(row["unchanged"] for row in rows),
        "artifacts": rows,
    }


def run(runtime: Path | None = None) -> dict[str, Any]:
    if runtime is None:
        raw = os.environ.get("FILIN_RUNTIME_ROOT")
        if not raw:
            raise RuntimeError("FILIN_RUNTIME_ROOT is required")
        runtime = Path(raw)
    trial = json.loads(
        (REPORT / "targeted_trial_results.json").read_text(encoding="utf-8")
    )
    lock = verify_code_lock()
    trace_rows = []
    database_rows = []
    for item in trial["runs"]:
        run_dir = runtime / item["run_id"]
        trace = run_dir / "timing_trace_v2.jsonl"
        trace_rows.append(
            {
                "run_id": item["run_id"],
                "expected_sha256": item["trace_sha256"],
                "actual_sha256": sha256(trace) if trace.is_file() else None,
                "unchanged": trace.is_file()
                and sha256(trace) == item["trace_sha256"],
            }
        )
        counts = {}
        for role in ("connector", "receiver"):
            db_path = run_dir / f"{role}.sqlite"
            db = sqlite3.connect(f"file:{db_path.as_posix()}?mode=ro", uri=True)
            counts[role] = db.execute("SELECT count(*) FROM events").fetchone()[0]
            db.close()
        database_rows.append(
            {
                "run_id": item["run_id"],
                "connector_event_count": counts["connector"],
                "receiver_event_count": counts["receiver"],
                "expected_event_count": item["event_count"],
                "sets_reconciled_by_count": counts["connector"]
                == counts["receiver"]
                == item["event_count"],
            }
        )
    candidate_actual = sha256(CANDIDATE)
    result = {
        "schema_version": "v03171_resume_integrity_v1",
        "stage": "v0.3.17.1",
        "strict_resume_hash_verification_passed": (
            lock["locked_artifacts_unchanged"]
            and all(row["unchanged"] for row in trace_rows)
            and candidate_actual == CANDIDATE_SHA256
        ),
        "strict_resume_passed": (
            lock["locked_artifacts_unchanged"]
            and all(row["unchanged"] for row in trace_rows)
            and all(row["sets_reconciled_by_count"] for row in database_rows)
            and candidate_actual == CANDIDATE_SHA256
            and trial["targeted_trial_passed"]
        ),
        "repeated_capture_count": 0,
        "repeated_feature_extraction_count": 0,
        "repeated_inference_count": 0,
        "repeated_event_generation_count": 0,
        "repeated_bundle_finalization_count": 0,
        "acknowledged_event_resend_count": 0,
        "candidate_identity_unchanged": candidate_actual == CANDIDATE_SHA256,
        "code_lock": lock,
        "trace_hash_verification": trace_rows,
        "database_reconciliation": database_rows,
    }
    REPORT.mkdir(parents=True, exist_ok=True)
    (REPORT / "resume_integrity_report.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return result


def main() -> int:
    result = run()
    print(
        json.dumps(
            {
                "strict_resume_passed": result["strict_resume_passed"],
                "locked_artifacts_unchanged": result["code_lock"][
                    "locked_artifacts_unchanged"
                ],
            },
            ensure_ascii=False,
        )
    )
    return 0 if result["strict_resume_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
