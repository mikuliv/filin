from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from tools.audit.validate_v0317_bundle import corruption_tests, validate


ROOT = Path(__file__).resolve().parents[3]
HISTORICAL_REPORT = ROOT / "ml/reports/v0_3_17"
REPORT = ROOT / "ml/reports/v0_3_17_1"

CASE_NAMES = (
    ("manifest", "unknown_schema_version"),
    ("manifest", "wrong_stage"),
    ("manifest", "wrong_revision"),
    ("artifact_hash", "hash_replaced_with_zero"),
    ("artifact_size", "negative_size"),
    ("artifact_path", "parent_path_escape"),
    ("artifact_path", "absolute_path"),
    ("artifact_path", "backslash_path"),
    ("artifact_list", "duplicate_path"),
    ("artifact_classification", "sensitive_flag_enabled"),
    ("artifact_classification", "git_permission_disabled"),
    ("artifact_hash", "hash_field_removed"),
    ("artifact_size", "size_field_removed"),
    ("artifact_path", "path_field_removed"),
    ("artifact_list", "artifact_list_removed"),
    ("artifact_list", "artifact_list_empty"),
    ("artifact_hash", "hash_replaced"),
    ("artifact_size", "size_incremented"),
    ("artifact_path", "missing_target"),
    ("manifest", "unsupported_schema_revision"),
)


def run() -> dict[str, Any]:
    structural = validate(HISTORICAL_REPORT)
    if not structural["passed"]:
        raise RuntimeError(f"canonical_bundle_invalid:{structural['errors']}")
    raw = corruption_tests(HISTORICAL_REPORT)
    cases = []
    for item, (artifact, mutation) in zip(raw["cases"], CASE_NAMES):
        case_id = int(item["case"])
        missed_historically = case_id in {15, 16}
        cases.append(
            {
                "case_id": case_id,
                "mutated_artifact": artifact,
                "mutation_type": mutation,
                "expected_rejection": True,
                "actual_result": "rejected" if item["rejected"] else "accepted",
                "validator_path": "tools/audit/validate_v0317_bundle.py",
                "root_cause": (
                    "The validator defaulted a missing artifacts field to an empty list "
                    "and did not require at least one manifest artifact."
                    if missed_historically
                    else "Existing structural validation rule."
                ),
                "security_impact": (
                    "An empty evidence manifest could be accepted as a valid bundle."
                    if missed_historically
                    else "Malformed evidence is rejected before use."
                ),
                "fix": (
                    "Require artifacts to be a non-empty list before iterating."
                    if missed_historically
                    else "No additional correction required."
                ),
                "regression_test": (
                    "test_corruption_suite_rejects_all_twenty_cases"
                    if missed_historically
                    else "full_corruption_matrix"
                ),
                "rejected": item["rejected"],
            }
        )
    result = {
        "schema_version": "v03171_corruption_suite_v1",
        "stage": "v0.3.17.1",
        "canonical_v0317_bundle_modified": False,
        "canonical_bundle_structural_validation_passed": structural["passed"],
        "historically_unrejected_case_ids": [15, 16],
        "corruption_case_count": len(cases),
        "corruption_rejected_count": sum(row["rejected"] for row in cases),
        "corruption_suite_passed": all(row["rejected"] for row in cases),
        "cases": cases,
    }
    REPORT.mkdir(parents=True, exist_ok=True)
    (REPORT / "corruption_suite_report.json").write_text(
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
                "corruption_case_count": result["corruption_case_count"],
                "corruption_rejected_count": result["corruption_rejected_count"],
                "passed": result["corruption_suite_passed"],
            },
            ensure_ascii=False,
        )
    )
    return 0 if result["corruption_suite_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
