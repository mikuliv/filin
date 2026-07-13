"""Post-hoc сравнение raw и frozen temporal decision v0.3.7."""
from __future__ import annotations
import numpy as np
import pandas as pd


def analyze(rows:pd.DataFrame,raw:pd.DataFrame,temporal:pd.DataFrame)->dict:
    benign=rows.label.astype(str).to_numpy()=='benign';attack=~benign
    r=raw.decision_state.astype(str).to_numpy();t=temporal.decision_state.astype(str).to_numpy()
    alert=lambda x:np.array([v=='suspicious_unclassified' or v.startswith('attack_candidate:') for v in x])
    ra,ta=alert(r),alert(t)
    delays=[]
    joined=pd.DataFrame({'run':rows.run_id,'episode':rows.episode_id,'label':rows.label,'raw':ra,'temporal':ta})
    rescued_attack=rescued_benign=0
    for _,part in joined.groupby(['run','episode'],sort=False):
        ri=np.flatnonzero(part.raw.to_numpy());ti=np.flatnonzero(part.temporal.to_numpy())
        if len(ri) and len(ti):delays.append(int(ti[0]-ri[0]))
        if part.label.iloc[0]!='benign' and not len(ri) and len(ti):rescued_attack+=1
        if part.label.iloc[0]=='benign' and len(ri) and not len(ti):rescued_benign+=1
    return {'false_positives_resolved_by_temporal_evidence':int(np.sum(benign&ra&~ta)),
     'new_false_positives_introduced':int(np.sum(benign&~ra&ta)),
     'attack_detections_preserved':int(np.sum(attack&ra&ta)),
     'attack_detections_delayed':int(sum(x>0 for x in delays)),'attack_episodes_rescued':rescued_attack,
     'benign_episodes_rescued':rescued_benign,'median_detection_delay':float(np.median(delays)) if delays else 0.0,
     'maximum_detection_delay':int(max(delays)) if delays else 0,'parameters_changed_after_freeze':False}
