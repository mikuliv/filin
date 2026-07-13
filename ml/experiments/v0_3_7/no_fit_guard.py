"""Runtime-аудит validation: любые training/tuning операции запрещены."""


class NoFitGuard:
 def __init__(self):
  self.fit_call_count=0;self.partial_fit_call_count=0;self.blocked_operations=[]
 def _deny(self,name,*args,**kwargs):
  self.blocked_operations.append(name)
  if name=='partial_fit':self.partial_fit_call_count+=1
  else:self.fit_call_count+=1
  raise RuntimeError(f'{name} запрещён на internal validation')
 def fit(self,*args,**kwargs):return self._deny('fit',*args,**kwargs)
 def fit_transform(self,*args,**kwargs):return self._deny('fit_transform',*args,**kwargs)
 def partial_fit(self,*args,**kwargs):return self._deny('partial_fit',*args,**kwargs)
 def calibrate(self,*args,**kwargs):return self._deny('calibrate',*args,**kwargs)
 def optimize_thresholds(self,*args,**kwargs):return self._deny('threshold_optimization',*args,**kwargs)
 def select_features(self,*args,**kwargs):return self._deny('feature_selection',*args,**kwargs)
 def tune_ood(self,*args,**kwargs):return self._deny('ood_tuning',*args,**kwargs)
 def tune_temporal(self,*args,**kwargs):return self._deny('temporal_tuning',*args,**kwargs)
 def change_rolling_depth(self,*args,**kwargs):return self._deny('rolling_depth_change',*args,**kwargs)
 def audit(self):
  return {'fit_call_count':self.fit_call_count,'partial_fit_call_count':self.partial_fit_call_count,
   'blocked_operations':self.blocked_operations,'calibration_performed_on_validation':False,
   'threshold_tuning_performed_on_validation':False,'feature_selection_performed_on_validation':False,
   'ood_tuning_performed_on_validation':False,'temporal_tuning_performed_on_validation':False,
   'model_refit_on_validation':False}
