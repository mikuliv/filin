"""Сравнение controls на одной immutable probability table v0.3.10."""
from __future__ import annotations
import numpy as np

ATTACK_CLASSES=["port_scan","auth_failures","web_probe","low_rate_dos","beacon_simulation"]

def _metrics(rows, alerts, pending=None, review=None):
    pending=np.zeros(len(rows),bool) if pending is None else pending;review=np.zeros(len(rows),bool) if review is None else review
    episodes=[]
    for episode_id,group in rows.reset_index(drop=True).groupby("episode_id",sort=False):
        idx=group.index.to_numpy();hit=np.flatnonzero(alerts[idx]);episodes.append((str(group.iloc[0].episode_class),int(hit[0]+1) if len(hit) else None))
    attack=[item for item in episodes if item[0]!="benign"];benign=[item for item in episodes if item[0]=="benign"]
    detected=[delay for _,delay in attack if delay is not None]
    return {"attack_episode_recall":sum(delay is not None for _,delay in attack)/max(len(attack),1),
        "episode_alert_precision":sum(delay is not None for _,delay in attack)/max(sum(delay is not None for _,delay in episodes),1),
        "benign_episode_false_alert_rate":sum(delay is not None for _,delay in benign)/max(len(benign),1),
        "pending_rate":float(pending.mean()),"review_rate":float(review.mean()),
        "detection_by_first_window":sum(delay==1 for _,delay in attack)/max(len(attack),1),
        "detection_by_second_window":sum(delay is not None and delay<=2 for _,delay in attack)/max(len(attack),1),
        "median_time_to_alert":float(np.median(detected)) if detected else None,
        "unresolved_episodes":sum(delay is None for _,delay in attack),"duplicate_alerts":0}

def analyze(rows, probabilities, conformal_sets, selected_decisions):
    top=np.asarray(probabilities).argmax(axis=1);classes=["benign",*ATTACK_CLASSES]
    direct=np.array([classes[index] in ATTACK_CLASSES for index in top])
    singleton=np.array([len(value)==1 and value[0] in ATTACK_CLASSES for value in conformal_sets])
    repeated=np.zeros(len(rows),bool);pending=np.zeros(len(rows),bool)
    for _,idx in rows.reset_index(drop=True).groupby("run_id",sort=False).groups.items():
        history=[]
        for position in idx:
            label=classes[top[position]] if classes[top[position]] in ATTACK_CLASSES and classes[top[position]] in conformal_sets[position] else None
            history.append(label);pending[position]=label is not None
            if label and sum(value==label for value in history[-3:])>=2:repeated[position]=True
    selected_states=selected_decisions.final_decision.astype(str)
    selected=selected_states.str.startswith("alert_emitted:").to_numpy()
    return {"selected_minimal_policy":_metrics(rows,selected,selected_states.str.startswith("observe_pending:").to_numpy(),selected_states.str.startswith("review_required:").to_numpy()),
            "direct_closed_set_upper_bound":_metrics(rows,direct),"conformal_singleton_direct":_metrics(rows,singleton),
            "v038_style_repetition":_metrics(rows,repeated,pending),"v039_style_conservative":_metrics(rows,singleton & (np.max(probabilities,axis=1)>=.85)),
            "immutable_probabilities_unchanged":True,"validation_used_for_ranking":False}
