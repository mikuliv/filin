"""Причинный accumulator решений v0.3.7."""
from __future__ import annotations
from collections import deque
class TemporalEvidenceAccumulator:
 def __init__(self,variant='none',alpha=.7,activation_threshold=.65):self.variant=variant;self.alpha=alpha;self.activation_threshold=activation_threshold;self.history=deque(maxlen=4);self.evidence=0.0;self.run_id=None
 def reset(self,run_id=None):self.history.clear();self.evidence=0.0;self.run_id=run_id
 def update(self,probability,run_id=None):
  if run_id!=self.run_id:self.reset(run_id)
  p=float(probability);self.history.append(p)
  if self.variant=='2_of_3':return sum(x>=.5 for x in list(self.history)[-3:])>=2
  if self.variant=='2_of_4':return sum(x>=.5 for x in self.history)>=2
  if self.variant=='decayed':self.evidence=self.alpha*self.evidence+(1-self.alpha)*p;return self.evidence>=self.activation_threshold
  return p>=.5
