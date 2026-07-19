"""Запрет любого обучения и выбора параметров в v0.3.12."""
from __future__ import annotations
from unittest.mock import patch

COUNTERS=("fit_call_count","partial_fit_call_count","fit_transform_call_count","calibration_call_count","conformal_fit_call_count","threshold_selection_call_count","feature_selection_call_count","candidate_replacement_count","docker_campaign_call_count","zeek_processing_call_count","feature_extraction_call_count")

class NoFitGuard:
    def __init__(self): self.counters={name:0 for name in COUNTERS}; self._patches=[]
    def _blocked(self, counter):
        def call(*_a,**_k): self.counters[counter]+=1; raise RuntimeError(f"v0.3.12 no-fit guard: {counter}")
        return call
    def __enter__(self):
        from sklearn.base import BaseEstimator, TransformerMixin
        from sklearn.ensemble import HistGradientBoostingClassifier
        for obj,name,counter in [(BaseEstimator,"fit","fit_call_count"),(HistGradientBoostingClassifier,"fit","fit_call_count"),(TransformerMixin,"fit_transform","fit_transform_call_count")]:
            p=patch.object(obj,name,self._blocked(counter),create=True); p.start(); self._patches.append(p)
        return self
    def __exit__(self,*_):
        for p in reversed(self._patches): p.stop()
    def report(self): return {**self.counters,"no_fit_audit_passed":all(v==0 for v in self.counters.values())}
