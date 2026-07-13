"""IsolationForest OOD guard: OOD означает insufficient evidence, не attack."""
from __future__ import annotations
import numpy as np
from sklearn.ensemble import IsolationForest
class BenignOODGuard:
 def __init__(self,quantile=.975):self.quantile=quantile;self.model=IsolationForest(n_estimators=300,max_samples='auto',contamination='auto',random_state=42,n_jobs=-1);self.threshold=None
 def fit(self,X):self.model.fit(X);scores=-self.model.score_samples(X);self.threshold=float(np.quantile(scores,self.quantile));return self
 def score(self,X):return -self.model.score_samples(X)
 def is_ood(self,X):return self.score(X)>self.threshold
