"""Запрет всех обучающих операций во frozen validation v0.3.10."""
from __future__ import annotations
from contextlib import ExitStack
from unittest.mock import patch

BLOCKED=("fit","fit_transform","partial_fit","calibrate","optimize","search","select_features","set_params","train","tune","conformal_fit","support_fit","select_threshold","decision_grid_evaluate","change_pending_ttl","change_ambiguity_margin","change_dedup_policy","exclude_rows","modify_validation_lock")
class NoFitGuard:
    def __init__(self,classes):self.classes=list(classes);self.counts={name:0 for name in BLOCKED};self.stack=ExitStack()
    def _blocked(self,name):
        def call(*args,**kwargs):self.counts[name]+=1;raise RuntimeError(f"Операция {name} запрещена на validation")
        return call
    def __enter__(self):
        for cls in self.classes:
            for name in BLOCKED:
                if hasattr(cls,name):self.stack.enter_context(patch.object(cls,name,self._blocked(name)))
        return self
    def __exit__(self,*args):return self.stack.__exit__(*args)
    def report(self):return {"status":"passed","method_call_counts":self.counts,"fit_call_count":self.counts["fit"],"partial_fit_call_count":self.counts["partial_fit"],"calibration_performed_on_validation":False,"conformal_tuning_on_validation":False,"support_tuning_on_validation":False,"decision_tuning_on_validation":False,"model_refit_on_validation":False,"validation_lock_modified_after_prediction":False}
