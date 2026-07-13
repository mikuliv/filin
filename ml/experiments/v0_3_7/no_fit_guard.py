"""Runtime audit validation: любые training/tuning операции запрещены."""
class NoFitGuard:
 def __init__(self):self.fit_call_count=0;self.partial_fit_call_count=0
 def blocked(self,*args,**kwargs):self.fit_call_count+=1;raise RuntimeError('Fit/tuning запрещён на internal validation')
 def audit(self):return {'fit_call_count':self.fit_call_count,'partial_fit_call_count':self.partial_fit_call_count,'calibration_performed_on_validation':False,'threshold_tuning_performed_on_validation':False,'feature_selection_performed_on_validation':False,'ood_tuning_performed_on_validation':False,'temporal_tuning_performed_on_validation':False,'model_refit_on_validation':False}
