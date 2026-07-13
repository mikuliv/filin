"""Frozen hierarchical decision architecture network_sensor_v0_5."""
from __future__ import annotations
import numpy as np
from ml.decision.v037_temporal_evidence import TemporalEvidenceAccumulator
class HierarchicalSensor:
 def __init__(self,gate,subtype,gate_calibrator,subtype_calibrator,ood_guard,benign_threshold=.3,attack_threshold=.7,subtype_threshold=.45,temporal_variant='2_of_3',temporal_parameters=None):
  self.gate=gate;self.subtype=subtype;self.gate_calibrator=gate_calibrator;self.subtype_calibrator=subtype_calibrator;self.ood_guard=ood_guard;self.benign_threshold=benign_threshold;self.attack_threshold=attack_threshold;self.subtype_threshold=subtype_threshold;self.temporal_variant=temporal_variant;self.temporal_parameters=temporal_parameters or {};self.subtype_call_count=0
 def gate_probability(self,X):
  raw=self.gate.predict_proba(X)[:,list(self.gate.classes_).index(1)];return self.gate_calibrator.predict_proba(raw)[:,list(self.gate_calibrator.model.classes_).index(1)]
 def decide(self,X,run_ids=None):
  probabilities=self.gate_probability(X);ood=self.ood_guard.is_ood(X);states=[];subtypes=[];acc=TemporalEvidenceAccumulator(self.temporal_variant,**self.temporal_parameters)
  run_ids=run_ids if run_ids is not None else [None]*len(probabilities)
  for index,(p,out,run_id) in enumerate(zip(probabilities,ood,run_ids)):
   temporal=acc.update(p,run_id)
   if out and not temporal:states.append('insufficient_evidence');subtypes.append(None);continue
   if p<=self.benign_threshold:states.append('benign');subtypes.append(None);continue
   if p<self.attack_threshold and not temporal:states.append('insufficient_evidence');subtypes.append(None);continue
   self.subtype_call_count+=1;raw=self.subtype.predict_proba(X[index:index+1]);cal=self.subtype_calibrator.predict_proba(raw)[0];position=int(np.argmax(cal));name=str(self.subtype_calibrator.model.classes_[position]);confidence=float(cal[position])
   if confidence<self.subtype_threshold:states.append('suspicious_unclassified');subtypes.append(None)
   else:states.append(f'attack_candidate:{name}');subtypes.append(name)
  return states,probabilities,ood,subtypes
