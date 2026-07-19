from __future__ import annotations
from contextlib import AbstractContextManager
from pathlib import Path
from unittest.mock import patch

class HistoricalReadOnlyGuard(AbstractContextManager):
    def __init__(self, roots):
        self.roots = tuple(Path(p).resolve() for p in roots)
        self.read_count = 0; self.blocked_write_count = 0; self._patcher = None; self._original = Path.open

    def _inside(self, path):
        p = Path(path).resolve()
        return any(p == root or root in p.parents for root in self.roots)

    def __enter__(self):
        guard = self
        def checked(path, mode="r", *args, **kwargs):
            if guard._inside(path):
                if any(x in mode for x in "wax+"):
                    guard.blocked_write_count += 1
                    raise PermissionError(f"Исторический источник доступен только для чтения: {path}")
                guard.read_count += 1
            return guard._original(path, mode, *args, **kwargs)
        self._patcher = patch.object(Path, "open", checked); self._patcher.start(); return self

    def __exit__(self, *exc):
        self._patcher.stop(); return False

    def report(self):
        return {"allowed_read_count": self.read_count, "blocked_write_count": self.blocked_write_count,
                "historical_read_only_guard_passed": self.blocked_write_count == 0}

