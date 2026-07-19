from __future__ import annotations
from collections import defaultdict,Counter
from statistics import mean,median
from .common import canonical_label,ATTACK_CLASSES,sha256_json

def canonical_sort(records):
    required=("benchmark_id","run_id","activity_key","causal_order","immutable_row_id")
    for row in records:
        if any(row.get(k) is None for k in required): raise ValueError("causal mapping incomplete")
    seen=set()
    for row in records:
        key=(row["benchmark_id"],row["run_id"],row["activity_key"],row["causal_order"])
        if key in seen: raise ValueError("duplicate causal_order within activity key")
        seen.add(key)
    return sorted(records,key=lambda r:(r["benchmark_id"],r["run_id"],r["activity_key"],r["causal_order"],r["immutable_row_id"]))

def evaluate(records,metadata):
    ordered=canonical_sort(records); groups=defaultdict(list); membership=set()
    for row in ordered:
        meta=metadata[row["immutable_row_id"]]; key=(row["run_id"],str(meta["episode_id"]))
        if row["immutable_row_id"] in membership: raise ValueError("duplicate episode row membership")
        membership.add(row["immutable_row_id"]); groups[key].append((row,meta))
    episodes=[]
    for (run,eid),rows in groups.items():
        rows.sort(key=lambda x:(x[0]["causal_order"],x[0]["immutable_row_id"])); label=canonical_label(rows[0][1].get("episode_class") or rows[0][1].get("label")); states=[r["primary_state"] for r,_ in rows]
        alerts=[i+1 for i,s in enumerate(states) if s.startswith("alert_emitted:")]; alert=alerts[0] if alerts else None
        strong=next((i+1 for i,(r,_) in enumerate(rows) if r["top_class"]==label and r["strong_evidence"]),None)
        weak=next((i+1 for i in range(1,len(rows)) if rows[i-1][0]["top_class"]==label==rows[i][0]["top_class"] and rows[i-1][0]["weak_evidence"] and rows[i][0]["weak_evidence"]),None)
        eligible=min([x for x in (strong,weak) if x is not None],default=None); extra=None if eligible is None or alert is None else alert-eligible
        episodes.append({"run_id":run,"episode_id":eid,"group":str(rows[0][1].get("environment_group") or rows[0][1].get("variant_id") or "unknown"),"label":label,"length":len(rows),"alert_window":alert,"earliest_strong_eligibility":strong,"earliest_weak_confirmation":weak,"state_machine_extra_delay":extra,"unresolved_pending":states[-1].startswith("pre_alert_pending:"),"review":any(s.startswith("review_required:") for s in states),"first_alert_suppressed":any("duplicate_alert_suppressed" in r["event_flags"] for r,_ in rows[:1])})
    attacks=[e for e in episodes if e["label"]!="benign"]; benign=[e for e in episodes if e["label"]=="benign"]; detected=[e for e in attacks if e["alert_window"]]; false=[e for e in benign if e["alert_window"]]
    def subset(rows):
        attack_rows=[e for e in rows if e["label"]!="benign"]; alerts=[e["alert_window"] for e in attack_rows if e["alert_window"]]
        return {"episode_count":len(rows),"attack_episode_count":len(attack_rows),"attack_episode_recall":len(alerts)/max(len(attack_rows),1),"detection_by_first_window":sum(x<=1 for x in alerts)/max(len(attack_rows),1),"detection_by_second_window":sum(x<=2 for x in alerts)/max(len(attack_rows),1),"detection_by_third_window":sum(x<=3 for x in alerts)/max(len(attack_rows),1),"detection_by_fourth_window":sum(x<=4 for x in alerts)/max(len(attack_rows),1),"alert_window_counts":{str(i):sum(x==i for x in alerts) for i in range(1,5)}}
    def breakdown(field): return {str(v):subset([e for e in episodes if e[field]==v]) for v in sorted({e[field] for e in episodes},key=str)}
    latencies=[e["alert_window"] for e in detected]; per_class={c:sum(e["alert_window"] is not None for e in attacks if e["label"]==c)/max(sum(e["label"]==c for e in attacks),1) for c in ATTACK_CLASSES}
    result={**subset(episodes),"benign_episode_count":len(benign),"episode_alert_precision":len(detected)/max(len(detected)+len(false),1),"benign_episode_false_alert_rate":len(false)/max(len(benign),1),"latency":{"mean":mean(latencies) if latencies else None,"median":median(latencies) if latencies else None,"maximum":max(latencies,default=None)},"per_class_episode_recall":per_class,"per_class":breakdown("label"),"per_run":breakdown("run_id"),"per_group":breakdown("group"),"per_episode_length":breakdown("length"),"unresolved_pending_episode_count":sum(e["unresolved_pending"] for e in attacks),"unresolved_pending_episode_rate":sum(e["unresolved_pending"] for e in attacks)/max(len(attacks),1),"pre_alert_pending_episode_rate":sum(e["earliest_weak_confirmation"] is not None and e["alert_window"] and e["alert_window"]>1 for e in attacks)/max(len(attacks),1),"first_alert_suppression_count":sum(e["first_alert_suppressed"] for e in episodes),"eligible_but_not_emitted_count":sum((e["state_machine_extra_delay"] or 0)>0 for e in attacks),"state_machine_extra_delay_count":sum((e["state_machine_extra_delay"] or 0)>0 for e in attacks),"episode_semantic_hash":sha256_json(episodes)}
    return result,episodes
