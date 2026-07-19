from __future__ import annotations

import os
import shutil
from contextlib import AbstractContextManager
from pathlib import Path
from unittest.mock import patch


class HistoricalReadOnlyGuard(AbstractContextManager):
    """Fail closed for every common filesystem mutation under frozen roots."""

    def __init__(self, roots):
        self.roots = tuple(Path(root).resolve() for root in roots)
        self.read_count = 0
        self.blocked_write_count = 0
        self.blocked_operations = []
        self._patches = []

    def _inside(self, value) -> bool:
        if isinstance(value, int):
            return False
        try:
            path = Path(value).resolve()
        except (TypeError, ValueError):
            return False
        return any(path == root or root in path.parents for root in self.roots)

    def _block(self, operation, *paths):
        if any(self._inside(path) for path in paths):
            self.blocked_write_count += 1
            self.blocked_operations.append({"operation": operation, "paths": [os.fspath(path) for path in paths]})
            raise PermissionError(f"Исторический источник доступен только для чтения: {operation}")

    def __enter__(self):
        guard = self
        original_open = Path.open

        def checked_open(path, mode="r", *args, **kwargs):
            if guard._inside(path):
                if any(flag in mode for flag in "wax+"):
                    guard._block("open:" + mode, path)
                guard.read_count += 1
            return original_open(path, mode, *args, **kwargs)

        self._patches.append(patch.object(Path, "open", checked_open))
        for name in ("unlink", "mkdir", "rmdir", "touch"):
            original = getattr(Path, name)

            def checked(path, *args, _name=name, _original=original, **kwargs):
                guard._block(_name, path)
                return _original(path, *args, **kwargs)

            self._patches.append(patch.object(Path, name, checked))
        for name in ("rename", "replace"):
            original = getattr(Path, name)

            def checked(path, target, *args, _name=name, _original=original, **kwargs):
                guard._block(_name, path, target)
                return _original(path, target, *args, **kwargs)

            self._patches.append(patch.object(Path, name, checked))
        for name in ("copyfile", "copy", "copy2"):
            original = getattr(shutil, name)

            def checked(source, destination, *args, _name=name, _original=original, **kwargs):
                guard._block(_name, destination)
                return _original(source, destination, *args, **kwargs)

            self._patches.append(patch.object(shutil, name, checked))
        for item in self._patches:
            item.start()
        return self

    def __exit__(self, *_exc):
        for item in reversed(self._patches):
            item.stop()
        return False

    def report(self):
        return {
            "allowed_read_count": self.read_count,
            "blocked_write_count": self.blocked_write_count,
            "blocked_operations": self.blocked_operations,
            "historical_read_only_guard_passed": self.blocked_write_count == 0,
            "protected_operations": ["create", "truncate", "rename", "replace", "unlink", "mkdir", "rmdir", "copy_destination", "temporary_output", "lockfile_creation"],
        }


__all__ = ["HistoricalReadOnlyGuard"]
