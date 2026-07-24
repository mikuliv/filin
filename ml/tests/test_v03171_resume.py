from __future__ import annotations

from ml.experiments.v0_3_17_1.resume import verify_code_lock


def test_pre_trial_code_lock_is_complete_and_unchanged() -> None:
    value = verify_code_lock()
    assert value["lock_revision"] == 2
    assert value["locked_artifact_count"] == 4
    assert value["locked_artifacts_unchanged"]
