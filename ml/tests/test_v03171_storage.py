from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
import yaml

from ml.experiments.v0_3_17_1.storage import MAX_BENCHMARK_BYTES, StorageLayout, run_storage_benchmark


ROOT = Path(__file__).resolve().parents[2]


def test_storage_layout_uses_environment_without_fixed_drive(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    runtime = tmp_path / "runtime"
    layout = StorageLayout.from_environment(
        {"FILIN_WORKSPACE": str(workspace), "FILIN_RUNTIME_ROOT": str(runtime)}
    )
    layout.prepare()
    assert layout.workspace == workspace.resolve()
    assert layout.runtime == runtime.resolve()
    assert all(layout.path(role).is_dir() for role in ("pcap", "zeek", "connector", "receiver"))


def test_process_environment_is_project_scoped(tmp_path: Path) -> None:
    layout = StorageLayout(tmp_path / "workspace", tmp_path / "runtime")
    values = layout.process_environment()
    assert values["TEMP"] == str(layout.runtime / "temp")
    assert values["TMP"] == values["TEMP"]
    assert values["PYTHONPYCACHEPREFIX"].startswith(str(layout.runtime))
    assert values["PIP_CACHE_DIR"].startswith(str(layout.runtime))


def test_sanitized_profile_has_tokens_and_no_drive_letters(tmp_path: Path) -> None:
    profile = StorageLayout(tmp_path / "workspace", tmp_path / "runtime").sanitized_profile()
    serialized = json.dumps(profile, ensure_ascii=False)
    assert "${FILIN_WORKSPACE}" in serialized
    assert "${FILIN_RUNTIME_ROOT}" in serialized
    assert re.search(r"\b[A-Za-z]:[\\/]", serialized) is None


def test_benchmark_is_bounded_and_removes_temporary_artifacts(tmp_path: Path) -> None:
    layout = StorageLayout(tmp_path / "workspace", tmp_path / "runtime")
    report = run_storage_benchmark(layout, max_bytes=2 << 20)
    assert report["temporary_bytes_requested"] == 2 << 20
    assert report["maximum_temporary_bytes"] == MAX_BENCHMARK_BYTES
    assert report["temporary_artifacts_removed"] is True
    assert not (layout.path("temp") / "storage-benchmark-v03171").exists()
    assert report["sequential_write_mib_per_second"] > 0
    assert report["sqlite_transactions_per_second"] > 0


@pytest.mark.parametrize("value", [0, -1, MAX_BENCHMARK_BYTES + 1])
def test_benchmark_rejects_unsafe_size(tmp_path: Path, value: int) -> None:
    with pytest.raises(ValueError, match="benchmark_size_out_of_bounds"):
        run_storage_benchmark(StorageLayout(tmp_path / "workspace", tmp_path / "runtime"), max_bytes=value)


def test_compose_uses_only_project_bind_mounts() -> None:
    compose = yaml.safe_load((ROOT / "rehearsal/docker-compose.v0_3_17_1.yml").read_text(encoding="utf-8"))
    assert "volumes" not in compose
    serialized = json.dumps(compose, ensure_ascii=False)
    for variable in (
        "FILIN_V03171_TRIAL_DIR",
        "FILIN_V03171_SENSOR_DIR",
        "FILIN_V03171_CONNECTOR_DIR",
        "FILIN_V03171_RECEIVER_DIR",
    ):
        assert variable in serialized


def test_tracked_storage_reports_contain_no_local_paths_or_serials() -> None:
    for name in ("storage_profile.json", "ssd_migration_verification_report.json"):
        text = (ROOT / "ml/reports/v0_3_17_1" / name).read_text(encoding="utf-8")
        assert re.search(r"\b[A-Za-z]:[\\/]", text) is None
        assert "838E" not in text

