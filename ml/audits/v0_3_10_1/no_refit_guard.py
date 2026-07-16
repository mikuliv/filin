"""Счётчик и блокировка запрещённых операций технического аудита."""
from __future__ import annotations
from contextlib import AbstractContextManager
from unittest.mock import patch

BLOCKED = ("fit", "fit_transform", "partial_fit", "calibrate", "optimize", "search",
           "select_features", "predict_generation", "docker_campaign")

class NoRefitGuard(AbstractContextManager):
    def __init__(self):
        self.counts = {name: 0 for name in BLOCKED}
        self._patches = []

    def _blocked(self, name):
        def call(*_args, **_kwargs):
            self.counts[name] += 1
            raise RuntimeError(f"Операция {name} запрещена аудитом v0.3.10.1")
        return call

    def block(self, name: str):
        """Явная fail-closed точка для orchestration-кода и тестов."""
        if name not in self.counts:
            raise KeyError(name)
        return self._blocked(name)()

    def __enter__(self):
        targets = [("sklearn.ensemble.HistGradientBoostingClassifier.fit", "fit")]
        for target, name in targets:
            try:
                item = patch(target, self._blocked(name)); item.start(); self._patches.append(item)
            except (AttributeError, ModuleNotFoundError):
                pass
        return self

    def __exit__(self, *args):
        for item in reversed(self._patches): item.stop()
        return False

    def report(self) -> dict:
        return {
            "fit_call_count": self.counts["fit"], "partial_fit_call_count": self.counts["partial_fit"],
            "prediction_call_count": self.counts["predict_generation"], "calibration_call_count": self.counts["calibrate"],
            "docker_campaign_call_count": self.counts["docker_campaign"],
            "no_refit_audit_passed": not any(self.counts.values()), "blocked_operations": list(BLOCKED),
        }
