from __future__ import annotations

from pathlib import Path


class BlindAccessAudit:
    def __init__(self, allowed: list[Path], denied: list[Path]):
        self.allowed = {Path(path).resolve() for path in allowed}
        self.denied = tuple(Path(path).resolve() for path in denied)
        self.counters = {"prediction_label_read_count": 0, "prediction_historical_row_read_count": 0, "prediction_historical_prediction_read_count": 0, "prediction_policy_result_read_count": 0}
        self.allowed_read_count = 0

    def read_bytes(self, path: Path) -> bytes:
        resolved = Path(path).resolve()
        if any(resolved == item or item in resolved.parents for item in self.denied):
            key = "prediction_label_read_count" if "label" in resolved.name else "prediction_historical_row_read_count"
            self.counters[key] += 1
            raise PermissionError(f"Blind prediction запрещён доступ к {resolved}")
        if resolved not in self.allowed:
            raise PermissionError(f"Путь отсутствует в prediction allowlist: {resolved}")
        self.allowed_read_count += 1
        return resolved.read_bytes()

    def report(self):
        return {**self.counters, "prediction_allowed_read_count": self.allowed_read_count, "blind_access_audit_passed": not any(self.counters.values())}
