from __future__ import annotations
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
for path in (ROOT,ROOT/'ml/features',ROOT/'ml/models',ROOT/'ml/decision',ROOT/'ml/experiments/v0_3_9',ROOT/'ml/analysis',ROOT/'lab/campaigns'):
 if str(path) not in sys.path:sys.path.insert(0,str(path))
from continuous_class_support import SupportResult
CLASSES=['benign','port_scan','auth_failures','web_probe','low_rate_dos','beacon_simulation']
def support(best='port_scan'):
 order=[best]+[x for x in CLASSES if x!=best];norm={x:.2+i*.2 for i,x in enumerate(order)};ranks={x:i+1 for i,x in enumerate(order)}
 return SupportResult(norm,norm,{x:1-norm[x] for x in CLASSES},ranks,{x:min(v for y,v in norm.items() if y!=x)-norm[x] for x in CLASSES},{x:1-norm[x] for x in CLASSES},order[0],order[1],norm[order[1]]-norm[order[0]])
def probabilities(top='port_scan',p=.92):
 rest=(1-p)/5;return {x:(p if x==top else rest) for x in CLASSES}
def record(top='port_scan',p=.92,strong=True):
 from v039_evidence_record import EvidenceThresholds,build_evidence_record
 return build_evidence_record(timestamp='2026-01-01T00:00:00+00:00',asset_state_key='asset',probabilities=probabilities(top,p),conformal_set=[top],conformal_p_values={x:(1 if x==top else 0) for x in CLASSES},support=support(top),thresholds=EvidenceThresholds(.85,.4,1,.1,.45,.8))
