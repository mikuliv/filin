from __future__ import annotations
import numpy as np
from .common import ATTACK_CLASSES

def evaluate(metadata, records):
    groups={}
    for meta,record in zip(metadata,records):
        key=(str(meta.get("run_id")),str(meta.get("episode_id")))
        groups.setdefault(key,[]).append((meta,record))
    attack=[]; benign=[]
    for rows in groups.values():
        label=str(rows[0][0].get("episode_class") or rows[0][0].get("label")); label="beacon" if label=="beacon_simulation" else label
        (benign if label=="benign" else attack).append((label,rows))
    detected=[]; correct=[]; latency=[]; per={c:[] for c in ATTACK_CLASSES}; unresolved=0
    for label,rows in attack:
        pos=next((i for i,(_,r) in enumerate(rows) if r["primary_state"].startswith("alert_emitted:")),None); ok=pos is not None; detected.append(ok); per.setdefault(label,[]).append(ok)
        if ok: latency.append(pos+1); correct.append(rows[pos][1]["top_class"]==label)
        if rows[-1][1]["primary_state"].startswith("pre_alert_pending:"): unresolved+=1
    false=sum(any(r["primary_state"].startswith("alert_emitted:") for _,r in rows) for _,rows in benign); alerts=sum(detected)+false
    by=lambda n:sum(x<=n for x in latency)/max(len(attack),1)
    return {"attack_episode_count":len(attack),"benign_episode_count":len(benign),"attack_episode_recall":float(np.mean(detected)) if detected else 0.,"episode_alert_precision":sum(correct)/max(alerts,1),"benign_episode_false_alert_rate":false/max(len(benign),1),"detection_by_first_window":by(1),"detection_by_second_window":by(2),"detection_by_third_window":by(3),"detection_by_fourth_window":by(4),"latency":{"mean":float(np.mean(latency)) if latency else None,"median":float(np.median(latency)) if latency else None,"maximum":max(latency) if latency else None},"unresolved_pending_episode_count":unresolved,"unresolved_pending_episode_rate":unresolved/max(len(attack),1),"per_class_episode_recall":{c:(float(np.mean(per[c])) if per.get(c) else None) for c in ATTACK_CLASSES}}

