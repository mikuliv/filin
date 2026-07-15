"""Причинное подавление повторных alert-emission v0.3.10."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AlertRecord:
    activity_state_key: str
    alert_class: str
    emitted_at: int
    dedup_expires_at: int
    source_path: str


class AlertDeduplicator:
    def __init__(self, ttl_windows: int = 3):
        self.ttl_windows = int(ttl_windows)
        self._records: dict[tuple[str, str], AlertRecord] = {}

    def reset(self, key: str | None = None) -> None:
        if key is None:
            self._records.clear()
        else:
            for item in [item for item in self._records if item[0] == key]:
                self._records.pop(item, None)

    def allowed(self, key: str, alert_class: str, window: int) -> bool:
        previous = self._records.get((key, alert_class))
        return previous is None or window > previous.dedup_expires_at

    def emit(self, key: str, alert_class: str, window: int, source_path: str) -> AlertRecord | None:
        if not self.allowed(key, alert_class, window):
            return None
        record = AlertRecord(key, alert_class, window, window + self.ttl_windows, source_path)
        self._records[(key, alert_class)] = record
        return record

