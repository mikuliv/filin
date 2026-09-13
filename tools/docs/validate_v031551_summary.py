from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

import yaml


CORRECTION_PATH = Path("docs/status/corrections/v0_3_15_5_scientific_reassessment.json")


def _git_blob(root: Path, revision: str, path: str) -> bytes | None:
    if not revision or not path or ":" in path or Path(path).is_absolute():
        return None
    commit = subprocess.run(
        ["git", "cat-file", "-e", f"{revision}^{{commit}}"], cwd=root, capture_output=True
    )
    if commit.returncode:
        return None
    result = subprocess.run(
        ["git", "show", f"{revision}:{path}"], cwd=root, capture_output=True
    )
    return result.stdout if result.returncode == 0 else None


def _stage_result(content: bytes, stage: str) -> tuple[str | None, list[str]]:
    try:
        value = yaml.safe_load(content.decode("utf-8"))
        row = next(item for item in value["stages"] if item["version"] == stage)
    except (UnicodeDecodeError, KeyError, StopIteration, TypeError, yaml.YAMLError):
        return None, []
    return row.get("result"), list(row.get("superseded_claims", []))


def validate_scientific_correction(
    root: Path, record: dict | None = None, current_revision: str = "HEAD"
) -> list[str]:
    failures: list[str] = []
    if record is None:
        path = root / CORRECTION_PATH
        if not path.is_file():
            return ["v03155_correction_record_missing"]
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            return ["v03155_correction_record_invalid"]
    if record.get("schema_version") != "filin_scientific_status_correction_v1":
        failures.append("v03155_correction_schema")
    if record.get("stage") != "v0.3.15.5" or record.get("status") != "accepted":
        failures.append("v03155_correction_status")
    historical = record.get("historical_state", {})
    corrected = record.get("corrected_state", {})
    historical_blob = _git_blob(root, historical.get("commit", ""), historical.get("path", ""))
    corrected_blob = _git_blob(root, corrected.get("commit", ""), corrected.get("path", ""))
    current_blob = _git_blob(root, current_revision, corrected.get("path", ""))
    if historical_blob is None:
        failures.append("v03155_historical_state_unavailable")
    elif _stage_result(historical_blob, record.get("stage", ""))[0] != historical.get("result"):
        failures.append("v03155_historical_state_mismatch")
    if corrected_blob is None:
        failures.append("v03155_correction_commit_unavailable")
    elif _stage_result(corrected_blob, record.get("stage", ""))[0] != corrected.get("result"):
        failures.append("v03155_correction_commit_mismatch")
    current_result, current_withdrawn = _stage_result(current_blob or b"", record.get("stage", ""))
    if current_result != corrected.get("result"):
        failures.append("v03155_current_state_mismatch")
    withdrawn = record.get("withdrawn_claims", [])
    if not withdrawn or not set(withdrawn).issubset(current_withdrawn):
        failures.append("v03155_withdrawn_claims_active")
    if record.get("frozen_outputs_rewritten") is not False:
        failures.append("v03155_frozen_outputs_policy")
    for item in record.get("unchanged_historical_artifacts", []):
        path = item.get("path", "")
        expected = item.get("sha256", "")
        correction_bytes = _git_blob(root, corrected.get("commit", ""), path)
        current_bytes = _git_blob(root, current_revision, path)
        if correction_bytes is None or current_bytes is None:
            failures.append(f"v03155_historical_artifact_unavailable:{path}")
        elif hashlib.sha256(correction_bytes).hexdigest() != expected:
            failures.append(f"v03155_historical_artifact_record_mismatch:{path}")
        elif current_bytes != correction_bytes:
            failures.append(f"v03155_historical_artifact_changed:{path}")
    return failures


def validate(root: Path) -> list[str]:
    status = yaml.safe_load((root / "docs/status/project-status.yaml").read_text(encoding="utf-8"))
    failures = []
    expected = {"current_candidate": "v03154:65a3dd912d845bc1", "latest_independent_model_holdout": "v0.3.15.5", "latest_runtime_trial": "v0.3.15.5.1"}
    for key, value in expected.items():
        if status.get(key) != value: failures.append(f"{key}_mismatch")
    for key in ("production_ready", "shadow_mode_ready", "backend_integration_ready", "automatic_enforcement_ready", "external_validation_completed"):
        if status.get(key) is not False: failures.append(f"{key}_must_be_false")
    versions = [item["version"] for item in status["stages"]]
    if "v0.3.15.5.1" not in versions or versions.index("v0.3.15.5.1") <= versions.index("v0.3.15.5"): failures.append("numeric_stage_order")
    if tuple(map(int, status["current_completed_stage"].removeprefix("v").split("."))) < (0, 3, 15, 5, 1): failures.append("current_completed_stage_regressed")
    failures.extend(validate_scientific_correction(root))
    required = [root / "docs/experiments/v0_3_15_5_1.md", root / "docs/contracts/shadow-event-v2.md", root / "collectors/shadow/contracts/candidate_registry_v1.json", root / "collectors/shadow/contracts/shadow_event_v2.schema.json"]
    if any(not path.is_file() for path in required): failures.append("required_reference_missing")
    text = "\n".join((root / name).read_text(encoding="utf-8") for name in ("README.md", "docs/status.md", "docs/current-capabilities.md", "docs/roadmap.md", "docs/experiments/v0_3_15_5_1.md"))
    for phrase in ("shadow_event_v1", "shadow_event_v2", "v0.3.15.5.1", "v0.3.16"):
        if phrase not in text: failures.append(f"missing_statement:{phrase}")
    if "превосходство над" in text.casefold() and "не заявляется" not in text.casefold(): failures.append("superiority_claim")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--root", default="."); parser.add_argument("--strict", action="store_true"); args = parser.parse_args()
    failures = validate(Path(args.root)); print(f"v0.3.15.5.1 documentation: {'passed' if not failures else 'failed'}")
    for failure in failures: print(f"- {failure}")
    return 1 if failures and args.strict else 0


if __name__ == "__main__": raise SystemExit(main())
