"""Причинное состояние умеренного сетевого evidence v0.3.10."""
from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass, field


@dataclass
class PendingRecord:
    pending_class: str
    first_seen_window: int
    last_seen_window: int
    confirmation_count: int = 1
    probability_history: list[float] = field(default_factory=list)
    margin_history: list[float] = field(default_factory=list)
    expires_after_windows: int = 3


class PendingState:
    """Хранит только прошлые и текущее окно в пределах activity key."""

    def __init__(self, ttl_windows: int = 3, repetition_policy: str = "two_of_three"):
        if ttl_windows not in (2, 3):
            raise ValueError("TTL pending должен быть равен двум или трём окнам")
        if repetition_policy not in ("two_consecutive", "two_of_three"):
            raise ValueError("Неизвестная политика подтверждения")
        self.ttl_windows = ttl_windows
        self.repetition_policy = repetition_policy
        self._history: dict[str, deque[tuple[int, str, float, float]]] = defaultdict(lambda: deque(maxlen=3))

    def reset(self, key: str | None = None) -> None:
        if key is None:
            self._history.clear()
        else:
            self._history.pop(key, None)

    def expire(self, key: str, window: int) -> None:
        history = self._history.get(key)
        if not history:
            return
        while history and window - history[0][0] >= self.ttl_windows:
            history.popleft()
        if not history:
            self._history.pop(key, None)

    def add(self, key: str, attack_class: str, window: int, probability: float, margin: float) -> tuple[bool, PendingRecord]:
        self.expire(key, window)
        history = self._history[key]
        history.append((window, attack_class, float(probability), float(margin)))
        same = [item for item in history if item[1] == attack_class]
        if self.repetition_policy == "two_consecutive":
            confirmed = len(history) >= 2 and history[-1][1] == history[-2][1] == attack_class and history[-1][0] == history[-2][0] + 1
        else:
            confirmed = len(same) >= 2 and same[-1][0] - same[-2][0] <= 2
        record = PendingRecord(attack_class, same[0][0], same[-1][0], len(same),
                               [item[2] for item in same], [item[3] for item in same], self.ttl_windows)
        return confirmed, record

    def confirmed_classes(self, key: str, window: int) -> list[str]:
        self.expire(key, window)
        history = self._history.get(key, ())
        return sorted({label for _, label, _, _ in history if sum(1 for item in history if item[1] == label) >= 2})

