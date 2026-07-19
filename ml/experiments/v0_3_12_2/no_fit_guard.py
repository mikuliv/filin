from __future__ import annotations
from contextlib import AbstractContextManager
from unittest.mock import patch

COUNTERS=("fit_call_count","partial_fit_call_count","fit_transform_call_count","calibration_fit_call_count","conformal_fit_call_count","threshold_selection_call_count","feature_selection_call_count","candidate_replacement_count","docker_campaign_call_count","zeek_processing_call_count","feature_extraction_call_count")
class NoFitGuard(AbstractContextManager):
    def __init__(self): self.counts={k:0 for k in COUNTERS}; self.patches=[]
    def blocked(self,name):
        def call(*_a,**_k): self.counts[name]+=1; raise RuntimeError(f"v0.3.12.2 запрещает {name}")
        return call
    def __enter__(self):
        from sklearn.base import BaseEstimator,TransformerMixin
        from sklearn.ensemble import HistGradientBoostingClassifier
        for obj,name,counter,create in ((BaseEstimator,"fit","fit_call_count",True),(BaseEstimator,"partial_fit","partial_fit_call_count",True),(TransformerMixin,"fit_transform","fit_transform_call_count",True),(HistGradientBoostingClassifier,"fit","fit_call_count",False)):
            p=patch.object(obj,name,self.blocked(counter),create=create); p.start(); self.patches.append(p)
        return self
    def __exit__(self,*_exc):
        for p in reversed(self.patches): p.stop()
        return False
    def report(self): return {**self.counts,"no_fit_audit_passed":not any(self.counts.values())}

class PredictionGuard:
    def __init__(self): self.counts={"v0.3.8_prediction_generation_count":0,"v0.3.9_prediction_generation_count":0,"v0.3.10_prediction_generation_count":0}
    def authorize(self,stage,output_exists=False):
        key=f"{stage}_prediction_generation_count"
        if stage!="v0.3.8": raise RuntimeError(f"Новая prediction запрещена для {stage}")
        if output_exists or self.counts[key]>=1: raise RuntimeError("Повторная prediction v0.3.8 запрещена")
        self.counts[key]+=1
    def report(self): return dict(self.counts)
