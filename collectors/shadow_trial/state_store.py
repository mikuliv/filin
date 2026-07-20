from __future__ import annotations

from pathlib import Path

from .common import read_json, sha256_json, write_json


class AtomicStateStore:
    def __init__(self, path: Path, key: dict):
        self.path = path
        self.key = key
        self.state = {"checkpoint_key_sha256": sha256_json(key), "completed_windows": {}, "sessions": {}, "export": {}, "checkpoint_count": 0}
        if path.exists():
            loaded = read_json(path)
            if loaded.get("checkpoint_key_sha256") != self.state["checkpoint_key_sha256"]:
                raise RuntimeError("Checkpoint key не совпадает с frozen inputs")
            self.state = loaded

    def completed(self, row_id: str) -> bool:
        return row_id in self.state["completed_windows"]

    def commit_window(self, row_id: str, record: dict) -> None:
        if row_id in self.state["completed_windows"]:
            raise RuntimeError("Повторный commit завершённого окна")
        self.state["completed_windows"][row_id] = record
        self.state["checkpoint_count"] += 1
        self._flush()

    def commit_session(self, session_id: str, record: dict) -> None:
        self.state["sessions"][session_id] = record
        self.state["checkpoint_count"] += 1
        self._flush()

    def _flush(self) -> None:
        temporary = self.path.with_suffix(".tmp")
        write_json(temporary, self.state)
        temporary.replace(self.path)
