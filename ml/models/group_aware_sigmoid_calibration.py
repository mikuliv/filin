"""Sigmoid calibration только по group-aware training OOF probabilities."""
from __future__ import annotations
import numpy as np
from sklearn.linear_model import LogisticRegression
class GroupAwareSigmoidCalibrator:
 def __init__(self):self.model=LogisticRegression(C=1.0,max_iter=2000,random_state=42);self.fitted=False
 def fit(self,probabilities,y):
  p=np.asarray(probabilities,float)
  if p.ndim==1:p=p[:,None]
  self.model.fit(np.log(np.clip(p,1e-6,1-1e-6)/(1-np.clip(p,1e-6,1-1e-6))),y);self.fitted=True;return self
 def predict_proba(self,probabilities):
  p=np.asarray(probabilities,float)
  if p.ndim==1:p=p[:,None]
  return self.model.predict_proba(np.log(np.clip(p,1e-6,1-1e-6)/(1-np.clip(p,1e-6,1-1e-6))))
 def parameters(self):return {'coef':self.model.coef_.tolist(),'intercept':self.model.intercept_.tolist(),'classes':self.model.classes_.tolist(),'method':'sigmoid'}
