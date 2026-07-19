from __future__ import annotations
from collections import Counter, defaultdict
from statistics import mean, median
from .delay_reason_taxonomy import primary_reason

ATTACK_CLASSES = ("port_scan", "auth_failures", "web_probe", "low_rate_dos", "beacon")

def canonical(label): return "beacon" if label == "beacon_simulation" else str(label)
def percentile(values, q):
    if not values: return None
    seq=sorted(values); pos=(len(seq)-1)*q; lo=int(pos); hi=min(lo+1,len(seq)-1)
    return seq[lo]+(seq[hi]-seq[lo])*(pos-lo)

def threshold_distances(record, label, policy):
    prob=float(record["joint_class_probabilities"].get(label, 0.)); others=[v for k,v in record["joint_class_probabilities"].items() if k != label]
    margin=prob-max(others or [0.]); benign=float(record["benign_probability"])
    return {
        "strong_probability_gap": max(0., policy["strong_probability"]-prob),
        "strong_margin_gap": max(0., policy["strong_margin"]-margin),
        "strong_benign_ceiling_excess": max(0., benign-policy["strong_benign_ceiling"]),
        "weak_probability_gap": max(0., policy["weak_probability"]-prob),
        "weak_margin_gap": max(0., policy["weak_margin"]-margin),
        "weak_benign_ceiling_excess": max(0., benign-policy["weak_benign_ceiling"]),
    }

def blockers(record, label, previous, policy):
    out=[]; top=record["top_class"]; cset=record["conformal_set"]
    if top == "benign": out.append("top_class_is_benign")
    elif top != label: out.extend(("top_class_is_wrong_attack", "true_class_not_top1"))
    if previous and previous["top_class"] != top: out.append("top_class_changed_since_previous_window")
    if not cset: out.append("conformal_empty")
    elif len(cset)>1: out.append("conformal_multi_class")
    elif cset[0] != label: out.append("conformal_wrong_singleton")
    if label not in cset: out.append("conformal_true_class_missing")
    if not (len(cset)==1 and cset[0] in ATTACK_CLASSES): out.append("conformal_not_attack_singleton")
    gaps=threshold_distances(record,label,policy)
    for key in ("strong_probability_gap","strong_margin_gap","strong_benign_ceiling_excess"):
        if gaps[key]>0: out.append(key.replace("_gap","_below_threshold").replace("_excess","_failed"))
    if top != label: out.append("strong_class_mismatch")
    if not record["strong_evidence"]: out.append("strong_not_eligible")
    for key in ("weak_probability_gap","weak_margin_gap","weak_benign_ceiling_excess"):
        if gaps[key]>0: out.append(key.replace("_gap","_below_threshold").replace("_excess","_failed"))
    if len(cset)!=1 or label not in cset: out.append("weak_conformal_conflict")
    if previous and previous["top_class"] != top: out.append("weak_class_instability")
    if record["weak_evidence"] and not previous: out.append("weak_first_observation_only")
    if record["weak_evidence"] and not str(record["primary_state"]).startswith(("alert_emitted:","post_alert_continuation:")): out.append("weak_repetition_not_confirmed")
    if not record["weak_evidence"]: out.append("weak_not_eligible")
    state=str(record["primary_state"])
    if state.startswith("review_ambiguous"): out.append("review_ambiguous")
    if state.startswith("review_novel"): out.append("review_novel")
    if "class_conflict" in state: out.append("review_class_conflict")
    return list(dict.fromkeys(out)), gaps

def audit(metadata, records, policy):
    by_id=metadata; groups=defaultdict(list)
    for r in records:
        m=by_id[r["immutable_row_id"]]; groups[(r["run_id"],str(m.get("episode_id")))].append((m,r))
    episodes=[]
    for (run,eid), rows in sorted(groups.items()):
        reported_alerts=[i+1 for i,(_,r) in enumerate(rows) if str(r["primary_state"]).startswith("alert_emitted:")]
        reported_emitted=reported_alerts[0] if reported_alerts else None
        rows.sort(key=lambda x:x[1]["causal_order"]); label=canonical(rows[0][0].get("episode_class") or rows[0][0].get("label"))
        if label == "benign": continue
        recs=[r for _,r in rows]; positions=[int(m.get("episode_position",i+1)) for i,(m,_) in enumerate(rows)]
        first=lambda pred: next((i+1 for i,r in enumerate(recs) if pred(r,i)),None)
        correct=first(lambda r,i:r["top_class"]==label)
        conformal=first(lambda r,i:r["conformal_set"]==[label])
        strong=first(lambda r,i:r["top_class"]==label and bool(r["strong_evidence"]))
        weak=first(lambda r,i:r["top_class"]==label and bool(r["weak_evidence"]))
        weak_confirm=next((i+1 for i in range(1,len(recs)) if recs[i-1]["top_class"]==label==recs[i]["top_class"] and recs[i-1]["weak_evidence"] and recs[i]["weak_evidence"]),None)
        eligible=min([x for x in (strong,weak_confirm) if x is not None],default=None)
        alerts=[i+1 for i,r in enumerate(recs) if str(r["primary_state"]).startswith("alert_emitted:")]
        emitted=alerts[0] if alerts else None; delayed=reported_emitted is None or reported_emitted>2
        all_blockers=[]; gaps=[]
        for i,r in enumerate(recs[:max((emitted or len(recs))-1,0)]):
            b,g=blockers(r,label,recs[i-1] if i else None,policy); all_blockers.extend(b); gaps.append(g)
        all_blockers=list(dict.fromkeys(all_blockers)); extra=None if eligible is None or emitted is None else emitted-eligible
        if reported_emitted != emitted:
            all_blockers.insert(0,"input_or_mapping_error")
        episodes.append({
            "benchmark_episode_key":f"{run}:{eid}", "run_id":run, "episode_id":eid, "true_class":label,
            "episode_length":len(rows), "episode_positions":positions, "alert_window":reported_emitted,
            "reported_alert_window":reported_emitted, "causal_alert_window":emitted,
            "alert_timing_class": "not_detected" if reported_emitted is None else (f"alert_window_{reported_emitted}" if reported_emitted<=3 else "alert_window_4_or_later"),
            "earliest_correct_top_class_window":correct, "earliest_correct_conformal_singleton_window":conformal,
            "earliest_strong_eligible_window":strong, "earliest_weak_evidence_window":weak,
            "earliest_weak_confirmable_window":weak_confirm, "earliest_policy_eligible_window":eligible,
            "actual_alert_emission_window":emitted, "state_machine_extra_delay":extra,
            "model_ready_by_second":correct is not None and correct<=2,
            "conformal_ready_by_second":conformal is not None and conformal<=2,
            "strong_ready_by_second":strong is not None and strong<=2,
            "weak_started_by_second":weak is not None and weak<=2,
            "weak_confirmed_by_second":weak_confirm is not None and weak_confirm<=2,
            "policy_ready_by_second":eligible is not None and eligible<=2,
            "alert_emitted_by_second":emitted is not None and emitted<=2,
            "delayed":delayed, "blockers":all_blockers, "primary_reason":primary_reason(all_blockers),
            "threshold_gaps":gaps,
            "activity_key_stable":len({r.get("activity_key") for r in recs})==1,
            "multiple_first_alerts":len(alerts)>1,
        })
    return summarize(episodes), episodes

def summarize(episodes):
    n=len(episodes); alerts=[e["alert_window"] for e in episodes if e["alert_window"]]
    causal_alerts=[e["causal_alert_window"] for e in episodes if e["causal_alert_window"]]
    delayed=[e for e in episodes if e["delayed"]]; timing=Counter(e["alert_timing_class"] for e in episodes)
    readiness={k:sum(bool(e[k]) for e in episodes) for k in ("model_ready_by_second","conformal_ready_by_second","strong_ready_by_second","weak_started_by_second","weak_confirmed_by_second","policy_ready_by_second","alert_emitted_by_second")}
    def breakdown(key):
        out={}
        for value in sorted({e[key] for e in episodes},key=str):
            rows=[e for e in episodes if e[key]==value]; ds=[e for e in rows if e["delayed"]]
            out[str(value)]={"episode_count":len(rows),"delayed_episode_count":len(ds),"delayed_rate":len(ds)/len(rows),"detection_by_second_rate":sum(e["alert_emitted_by_second"] for e in rows)/len(rows),"primary_reasons":dict(Counter(e["primary_reason"] for e in ds))}
        return out
    gap_values=defaultdict(list)
    for e in delayed:
        for row in e["threshold_gaps"]:
            for k,v in row.items(): gap_values[k].append(v)
    return {"attack_episode_count":n,"alert_timing_counts":dict(timing),"alert_window_counts":{str(i):sum(x==i for x in alerts) for i in range(1,4)},
            "causal_alert_window_counts":{str(i):sum(x==i for x in causal_alerts) for i in range(1,4)},
            "record_order_causal_order_mismatch_count":sum(e["reported_alert_window"]!=e["causal_alert_window"] for e in episodes),
            "detection_by_first_window":sum(x<=1 for x in alerts)/n,"detection_by_second_window":sum(x<=2 for x in alerts)/n,"detection_by_third_window":sum(x<=3 for x in alerts)/n,"episode_recall":len(alerts)/n,
            "latency":{"mean":mean(alerts),"median":median(alerts),"maximum":max(alerts)},"delayed_episode_count":len(delayed),"delayed_rate":len(delayed)/n,
            "primary_reason_counts":dict(Counter(e["primary_reason"] for e in delayed)),"full_blocker_combination_counts":dict(Counter("+".join(sorted(e["blockers"])) for e in delayed)),
            "readiness_by_second_counts":readiness,"state_machine_extra_delay_count":sum((e["state_machine_extra_delay"] or 0)>0 for e in episodes),
            "state_machine_extra_delay_distribution":dict(Counter(str(e["state_machine_extra_delay"]) for e in episodes)),
            "activity_key_anomaly_count":sum(not e["activity_key_stable"] for e in episodes),"per_class":breakdown("true_class"),"per_run":breakdown("run_id"),"per_episode_length":breakdown("episode_length"),
            "threshold_gap_summary":{k:{"mean":mean(v),"median":median(v),"p90":percentile(v,.9)} for k,v in gap_values.items()}}
