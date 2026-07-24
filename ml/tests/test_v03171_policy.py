from __future__ import annotations

from ml.experiments.v0_3_17_1.stage_result import (
    historical_v0317_status,
    identity_status,
)


def test_candidate_and_contract_anchors_are_unchanged() -> None:
    assert all(identity_status().values())


def test_historical_v0317_critical_artifacts_are_unchanged() -> None:
    assert all(historical_v0317_status().values())
