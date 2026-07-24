from __future__ import annotations

import json
from pathlib import Path

import pytest

from ml.experiments.v0_3_17_1.finalizer import (
    DETACHED_NAME,
    MANIFEST_NAME,
    FinalizationError,
    finalize,
    run_regression_report,
)


def lock(path: Path, stage: str = "v0.3.17.1", recovery: bool = False) -> None:
    path.write_text(
        json.dumps(
            {
                "schema_version": "v03171_finalizer_lock_v1",
                "stage": stage,
                "source_head": "1" * 40,
                "recovery_mode": recovery,
            }
        ),
        encoding="utf-8",
    )


def test_clean_finalization_and_resume(tmp_path: Path) -> None:
    report = tmp_path / "reports"
    report.mkdir()
    (report / "fixture.json").write_text("{}\n", encoding="utf-8")
    lock_path = report / "lock.json"
    lock(lock_path)
    first = finalize(report, lock_path, tmp_path, ("fixture.json",))
    second = finalize(report, lock_path, tmp_path, ("fixture.json",))
    assert first["clean_finalization_passed"]
    assert second["already_finalized"]
    assert (report / MANIFEST_NAME).is_file()
    assert (report / DETACHED_NAME).is_file()


@pytest.mark.parametrize(
    ("mode", "expected"),
    [
        ("missing", "lock_missing"),
        ("malformed", "lock_malformed"),
        ("other_stage", "lock_stage"),
        ("recovery", "recovery_mode_forbidden"),
    ],
)
def test_invalid_locks_fail_closed(
    tmp_path: Path, mode: str, expected: str
) -> None:
    report = tmp_path / "reports"
    report.mkdir()
    (report / "fixture.json").write_text("{}\n", encoding="utf-8")
    lock_path = report / "lock.json"
    if mode == "malformed":
        lock_path.write_text("{", encoding="utf-8")
    elif mode == "other_stage":
        lock(lock_path, "v0.3.17")
    elif mode == "recovery":
        lock(lock_path, recovery=True)
    with pytest.raises(FinalizationError, match=expected):
        finalize(report, lock_path, tmp_path, ("fixture.json",))


def test_path_confinement(tmp_path: Path) -> None:
    report = tmp_path / "reports"
    report.mkdir()
    lock_path = report / "lock.json"
    lock(lock_path)
    with pytest.raises(FinalizationError, match="path_confinement"):
        finalize(tmp_path.parent / "outside", lock_path, tmp_path, ())


def test_regression_matrix() -> None:
    value = run_regression_report()
    assert value["scenario_count"] == 9
    assert value["scenario_passed_count"] == 9
    assert value["finalizer_nameerror_fixed"]
    assert value["clean_finalization_passed"]
    assert value["recovery_finalization_required"] is False
