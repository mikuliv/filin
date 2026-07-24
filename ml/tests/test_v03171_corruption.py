from __future__ import annotations

import copy

import yaml

from ml.experiments.v0_3_17_1.corruption import HISTORICAL_REPORT, run
from tools.audit.validate_v0317_bundle import validate_manifest


def test_missing_artifact_list_is_rejected() -> None:
    value = yaml.safe_load(
        (HISTORICAL_REPORT / "v0_3_17_bundle_manifest.yaml").read_text(encoding="utf-8")
    )
    value.pop("artifacts")
    assert "artifacts_required" in validate_manifest(value, HISTORICAL_REPORT.parents[2])


def test_empty_artifact_list_is_rejected() -> None:
    value = yaml.safe_load(
        (HISTORICAL_REPORT / "v0_3_17_bundle_manifest.yaml").read_text(encoding="utf-8")
    )
    candidate = copy.deepcopy(value)
    candidate["artifacts"] = []
    assert "artifacts_required" in validate_manifest(
        candidate, HISTORICAL_REPORT.parents[2]
    )


def test_corruption_suite_rejects_all_twenty_cases() -> None:
    value = run()
    assert value["corruption_case_count"] == 20
    assert value["corruption_rejected_count"] == 20
    assert value["corruption_suite_passed"]
