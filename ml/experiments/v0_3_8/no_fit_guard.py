"""Fail-closed запрет любых training/tuning операций на validation."""
from __future__ import annotations


class NoFitGuard:
    def __init__(self):
        self.fit_call_count = 0
        self.partial_fit_call_count = 0
        self.blocked_operations: list[str] = []

    def _deny(self, name, *args, **kwargs):
        self.blocked_operations.append(name)
        if name == "partial_fit":
            self.partial_fit_call_count += 1
        else:
            self.fit_call_count += 1
        raise RuntimeError(f"Операция {name} запрещена на validation")

    fit = lambda self, *a, **k: self._deny("fit", *a, **k)
    fit_transform = lambda self, *a, **k: self._deny("fit_transform", *a, **k)
    partial_fit = lambda self, *a, **k: self._deny("partial_fit", *a, **k)
    calibrate = lambda self, *a, **k: self._deny("calibrate", *a, **k)
    optimize_thresholds = lambda self, *a, **k: self._deny("threshold_optimization", *a, **k)
    select_features = lambda self, *a, **k: self._deny("feature_selection", *a, **k)
    search_hyperparameters = lambda self, *a, **k: self._deny("hyperparameter_search", *a, **k)
    recalibrate_conformal = lambda self, *a, **k: self._deny("conformal_recalibration", *a, **k)
    change_conformal_alpha = lambda self, *a, **k: self._deny("conformal_alpha_change", *a, **k)
    refit_support = lambda self, *a, **k: self._deny("support_refit", *a, **k)
    change_support_threshold = lambda self, *a, **k: self._deny("support_threshold_change", *a, **k)
    change_episode_parameters = lambda self, *a, **k: self._deny("episode_parameter_change", *a, **k)

    def audit(self) -> dict:
        return {
            "fit_call_count": self.fit_call_count,
            "partial_fit_call_count": self.partial_fit_call_count,
            "blocked_operations": self.blocked_operations,
            "calibration_performed_on_validation": False,
            "conformal_tuning_on_validation": False,
            "support_tuning_on_validation": False,
            "episode_tuning_on_validation": False,
            "model_refit_on_validation": False,
        }
