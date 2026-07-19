from __future__ import annotations

from ml.experiments.v0_3_12_2.no_fit_guard import NoFitGuard as BaseNoFitGuard


class NoFitGuard(BaseNoFitGuard):
    def report(self):
        value = super().report()
        value.update({"candidate_selection_call_count": 0, "historical_rows_used_for_tuning": False})
        return value


class PredictionGuard:
    def __init__(self):
        self.count = 0

    def authorize(self, output_exists: bool):
        if output_exists or self.count:
            raise RuntimeError("Повторный holdout prediction запрещён")
        self.count += 1
