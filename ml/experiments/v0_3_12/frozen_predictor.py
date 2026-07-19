from __future__ import annotations
import sys
from pathlib import Path
import joblib, numpy as np, pandas as pd
from .common import ROOT, CLASSES, sha256_file
from .no_fit_guard import NoFitGuard

sys.path[:0]=[str(ROOT),str(ROOT/"ml/models")]
from ml.experiments.v0_3_10.pipeline import ATTACK_CLASSES as LEGACY_ATTACK_CLASSES, aligned_probabilities, calibrated_joint
from ml.experiments.v0_3_11.state_machine import BurdenAwareDecisionEngine, Evidence, Policy

EXPECTED_ARTIFACT="59d2cd75f3f09f5f8976fa2a56417ad10205986f696a3bef5a4fbaba52ff09b7"

def load_candidate(path: Path):
    if sha256_file(path)!=EXPECTED_ARTIFACT: raise RuntimeError("candidate artifact hash mismatch")
    return joblib.load(path)

def _policy(bundle):
    p=bundle["decision_parameters"]
    return Policy(p["strong_probability"],p["strong_margin"],p["strong_benign_ceiling"],p["weak_probability"],p["weak_margin"],p["weak_benign_ceiling"],p["repetition"],p["pending_ttl"],p["ambiguity_margin"],3,.80,.30)

def predict_block(bundle, X: pd.DataFrame, input_rows: list[dict], benchmark_id: str):
    with NoFitGuard() as guard:
        gate=aligned_probabilities(bundle["gate"],X,["0","1"])[:,1]
        subtype=aligned_probabilities(bundle["subtype"],X,LEGACY_ATTACK_CLASSES)
        probs=calibrated_joint(bundle["gate_calibrator"],bundle["subtype_calibrator"],gate,subtype)
        sets=bundle["conformal"].predict_set(probs)
    engine=BurdenAwareDecisionEngine(_policy(bundle)); records=[]; run_positions={}
    for row,p,cset in zip(input_rows,probs,sets):
        run=row["run_id"]; run_positions[run]=run_positions.get(run,0)+1
        display=["beacon" if x=="beacon_simulation" else str(x) for x in cset]
        top_i=int(np.argmax(p)); top=CLASSES[top_i]; ordered=np.sort(p); activity=row["activity_key_source"]
        ev=Evidence(run,activity,run_positions[run],top,float(p[top_i]),float(p[0]),float(ordered[-1]-ordered[-2]),tuple(display))
        d=engine.update(ev); flags=[name for name in ("duplicate_alert_suppressed","pending_started","pending_confirmed","pending_reset","pending_expired","class_conflict_detected","dedup_key_created","dedup_key_expired") if getattr(d,name,False)]
        jp={name:float(value) for name,value in zip(CLASSES,p)}
        records.append({"benchmark_id":benchmark_id,"run_id":run,"immutable_row_id":row["immutable_row_id"],"causal_order":row["causal_order"],"gate_probability":float(gate[len(records)]),"subtype_probabilities":{("beacon" if c=="beacon_simulation" else c):float(v) for c,v in zip(LEGACY_ATTACK_CLASSES,subtype[len(records)])},"joint_class_probabilities":jp,"calibrated_probabilities":jp,"conformal_set":display,"top_class":top,"top_probability":float(p[top_i]),"margin":float(ordered[-1]-ordered[-2]),"benign_probability":float(p[0]),"candidate_evidence":top!="benign","strong_evidence":top!="benign" and float(p[top_i])>=.70 and float(p[0])<=.20 and len(display)==1,"weak_evidence":top!="benign" and float(p[top_i])>=.35 and float(p[0])<=.45,"activity_key":activity,"primary_state":d.primary_state,"event_flags":flags,"alert_event_id":d.alert_event_id,"dedup_key":f"{run}:{activity}:{top}","state_transition_reason":d.primary_state})
    return records,guard.report()

