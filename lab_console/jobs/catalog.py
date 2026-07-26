from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import yaml

FORBIDDEN = {"push", "pull", "merge", "reset", "invoke-expression", "eval", "exec", "fit", "calibration", "threshold", "capture", "scan"}


class TaskCatalog:
    def __init__(self, path: Path) -> None:
        self.path = path
        raw = path.read_bytes().replace(b"\r\n", b"\n")
        self.sha256 = hashlib.sha256(raw).hexdigest()
        doc = yaml.safe_load(raw)
        self.tasks = {item["task_id"]: item for item in doc["tasks"]}
        self.validate()

    def validate(self) -> None:
        for task_id, task in self.tasks.items():
            if not isinstance(task.get("argv"), list) or not task["argv"]:
                raise ValueError(f"invalid_argv:{task_id}")
            text = " ".join(task["argv"]).lower()
            if any(word in text.split() for word in FORBIDDEN) or task.get("mutates_tracked_files"):
                raise ValueError(f"forbidden_task:{task_id}")
            if task.get("working_directory_token") not in {"repository_root", "runtime"}:
                raise ValueError(f"invalid_working_directory:{task_id}")

    def get(self, task_id: str) -> dict[str, Any]:
        if task_id not in self.tasks or not self.tasks[task_id].get("enabled"):
            raise KeyError("task_not_allowed")
        return self.tasks[task_id]
