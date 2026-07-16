"""Fail-closed validation no-fit guard."""
from contextlib import AbstractContextManager
from unittest.mock import patch
class ValidationNoFitGuard(AbstractContextManager):
 def __init__(self):self.counts={"fit":0,"partial_fit":0,"fit_transform":0,"calibration":0,"conformal_fit":0,"threshold_selection":0,"prediction_generation":0};self.patches=[]
 def blocked(self,name):
  def call(*a,**k):self.counts[name]+=1;raise RuntimeError(f"Validation operation {name} запрещена")
  return call
 def __enter__(self):
  for target,name in (("sklearn.ensemble.HistGradientBoostingClassifier.fit","fit"),("sklearn.preprocessing.StandardScaler.fit_transform","fit_transform")):
   p=patch(target,self.blocked(name));p.start();self.patches.append(p)
  return self
 def __exit__(self,*a):
  for p in reversed(self.patches):p.stop()
 def generated(self):self.counts["prediction_generation"]+=1
 def report(self):return {"validation_fit_call_count":self.counts["fit"],"validation_partial_fit_call_count":self.counts["partial_fit"],"validation_fit_transform_call_count":self.counts["fit_transform"],"validation_calibration_call_count":self.counts["calibration"],"validation_conformal_fit_call_count":self.counts["conformal_fit"],"validation_threshold_selection_call_count":self.counts["threshold_selection"],"validation_prediction_generation_count":self.counts["prediction_generation"],"no_fit_audit_passed":all(v==0 for k,v in self.counts.items() if k!="prediction_generation") and self.counts["prediction_generation"]==1}
