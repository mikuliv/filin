from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

from ml.experiments.v0_3_17_1.resume import verify_code_lock


def test_pre_trial_code_lock_is_complete_and_unchanged() -> None:
    value = verify_code_lock()
    assert value["lock_revision"] == 3
    assert value["locked_artifact_count"] == 4
    assert value["locked_artifacts_unchanged"]


def _git(root: Path, *args: str) -> str:
    return subprocess.check_output(
        ["git", *args], cwd=root, text=True, encoding="utf-8", errors="replace"
    ).strip()


def _lock_fixture(tmp_path: Path) -> tuple[Path, str]:
    _git(tmp_path, "init")
    _git(tmp_path, "config", "user.name", "Проверка")
    _git(tmp_path, "config", "user.email", "test@example.invalid")
    artifact = tmp_path / "artifact.txt"
    artifact.write_bytes(b"first\nsecond\n")
    _git(tmp_path, "add", "artifact.txt")
    _git(tmp_path, "commit", "-m", "Исходное состояние")
    source = _git(tmp_path, "rev-parse", "HEAD")
    lock = tmp_path / "lock.json"
    lock.write_text(json.dumps({
        "lock_revision": 3,
        "source_head": source,
        "locked_artifacts": [{
            "path": "artifact.txt",
            "sha256": hashlib.sha256(b"first\nsecond\n").hexdigest(),
        }],
    }), encoding="utf-8")
    return lock, source


def test_code_lock_is_independent_of_working_tree_eol(tmp_path):
    lock, _ = _lock_fixture(tmp_path)
    (tmp_path / "artifact.txt").write_bytes(b"first\r\nsecond\r\n")
    value = verify_code_lock(lock, tmp_path)
    assert value["locked_artifacts_unchanged"]
    assert not value["artifacts"][0]["working_tree_matches_blob"]


def test_code_lock_rejects_changed_git_blob(tmp_path):
    lock, _ = _lock_fixture(tmp_path)
    (tmp_path / "artifact.txt").write_bytes(b"first\nchanged\n")
    _git(tmp_path, "add", "artifact.txt")
    _git(tmp_path, "commit", "-m", "Подмена байта")
    assert not verify_code_lock(lock, tmp_path)["locked_artifacts_unchanged"]


def test_code_lock_fails_closed_without_source_head(tmp_path):
    lock, _ = _lock_fixture(tmp_path)
    value = json.loads(lock.read_text(encoding="utf-8"))
    value.pop("source_head")
    lock.write_text(json.dumps(value), encoding="utf-8")
    result = verify_code_lock(lock, tmp_path)
    assert not result["provenance_valid"]
    assert not result["locked_artifacts_unchanged"]


def test_code_lock_fails_closed_for_missing_path(tmp_path):
    lock, _ = _lock_fixture(tmp_path)
    value = json.loads(lock.read_text(encoding="utf-8"))
    value["locked_artifacts"][0]["path"] = "missing.txt"
    lock.write_text(json.dumps(value), encoding="utf-8")
    result = verify_code_lock(lock, tmp_path)
    assert not result["provenance_valid"]
    assert not result["locked_artifacts_unchanged"]
