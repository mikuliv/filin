from __future__ import annotations
from contextlib import AbstractContextManager
from unittest.mock import patch

COUNTER_NAMES = (
    "fit_call_count", "partial_fit_call_count", "calibration_call_count", "conformal_fit_call_count",
    "threshold_selection_call_count", "feature_selection_call_count", "candidate_replacement_count",
    "prediction_generation_count", "docker_campaign_call_count", "zeek_processing_call_count",
    "feature_extraction_call_count",
)

class NoFitNoPredictGuard(AbstractContextManager):
    def __init__(self):
        self.counters = {name: 0 for name in COUNTER_NAMES}
        self._patchers = []

    def _blocked(self, counter):
        def fail(*_args, **_kwargs):
            self.counters[counter] += 1
            raise RuntimeError(f"Запрещённая операция v0.3.12.1: {counter}")
        return fail

    def __enter__(self):
        from sklearn.base import BaseEstimator, TransformerMixin
        from sklearn.ensemble import HistGradientBoostingClassifier
        targets = ((BaseEstimator,"fit","fit_call_count",True),(TransformerMixin,"fit_transform","fit_call_count",True),
                   (HistGradientBoostingClassifier,"fit","fit_call_count",False),(HistGradientBoostingClassifier,"predict","prediction_generation_count",False),
                   (HistGradientBoostingClassifier,"predict_proba","prediction_generation_count",False))
        for obj,name,counter,create in targets:
            p=patch.object(obj,name,self._blocked(counter),create=create); p.start(); self._patchers.append(p)
        for target,counter in (("ml.experiments.v0_3_12.immutable_prediction.create","prediction_generation_count"),("ml.experiments.v0_3_12.frozen_predictor.load_candidate","prediction_generation_count")):
            p=patch(target,self._blocked(counter)); p.start(); self._patchers.append(p)
        return self

    def __exit__(self, *exc):
        for p in reversed(self._patchers): p.stop()
        return False

    def report(self):
        return {**self.counters, "no_fit_no_predict_audit_passed": not any(self.counters.values())}
