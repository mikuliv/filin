from __future__ import annotations
import statistics

def apply(compatibility, metrics, paired):
    evaluable=[x for x in compatibility["benchmarks"] if x["core_evaluable"]]; stateful=[x for x in evaluable if x["stateful_evaluable"]]; episode=[x for x in evaluable if x["episode_evaluable"]]
    coverage=len(evaluable)==5 and len(stateful)>=4 and len(episode)>=3 and any(x["benchmark_id"].startswith("v0310") and x["evaluation_mode"]=="full_stateful" for x in evaluable) and all(x["integrity_passed"] for x in compatibility["benchmarks"])
    window=[]; catastrophic=0; state=[]; eps=[]; conformal=[]
    for row in evaluable:
        m=metrics[row["benchmark_id"]]; ok=m["macro_f1"]>=.75 and m["balanced_accuracy"]>=.80 and m["benign_recall"]>=.75 and m["FPR"]<=.25 and m["attack_macro_recall"]>=.80 and not m["zero_recall_classes"]; window.append(ok)
        catastrophic+=m["benign_recall"]<.50 or m["FPR"]>.50 or m["attack_macro_recall"]<.50
        conformal.append(m["conformal"]["empirical_coverage_overall"]>=.80 and m["conformal"]["wrong_only_rate"]<=.10)
        if row["stateful_evaluable"]:
            s=m["stateful"]; state.append(m["candidate_evidence_recall"]>=.85 and m["strong_evidence_precision"]>=.90 and s["duplicate_suppression_precision"]>=.99 and s["duplicate_false_suppression_count"]==0 and s["cross_run_contamination_count"]==0 and s["cross_activity_contamination_count"]==0 and s["review_window_rate"]<=.25 and s["attack_review_window_rate"]<=.35 and s["pre_alert_pending_attack_window_rate"]<=.35)
        if row["episode_evaluable"]:
            e=m["episode"]; vals=[v for v in e["per_class_episode_recall"].values() if v is not None]; eps.append(e["attack_episode_recall"]>=.85 and e["episode_alert_precision"]>=.90 and e["benign_episode_false_alert_rate"]<=.10 and e["detection_by_second_window"]>=.75 and e["unresolved_pending_episode_rate"]<=.15 and (not vals or min(vals)>=.666667))
    agg={}
    for k in ("macro_f1","balanced_accuracy","benign_recall","FPR","attack_macro_recall"):
        vals=[metrics[x["benchmark_id"]][k] for x in evaluable]; agg[k]={"median":statistics.median(vals) if vals else None,"minimum":min(vals) if vals else None,"maximum":max(vals) if vals else None}
    aggregate=bool(evaluable) and agg["macro_f1"]["median"]>=.90 and agg["balanced_accuracy"]["median"]>=.90 and agg["benign_recall"]["median"]>=.90 and agg["FPR"]["median"]<=.10 and agg["attack_macro_recall"]["median"]>=.90 and catastrophic==0
    non_inferiority=all(all((k=="FPR" and v<=.02) or (k!="FPR" and v>=-.02) for k,v in row["metric_deltas"].items()) for row in paired["benchmarks"])
    flags={"evaluation_coverage_policy_passed":coverage,"all_absolute_window_gates_passed":bool(window) and all(window),"all_stateful_gates_passed":bool(state) and all(state),"all_episode_gates_passed":bool(eps) and all(eps),"cross_benchmark_aggregate_policy_passed":aggregate,"non_inferiority_policy_passed":non_inferiority,"catastrophic_regression_absent":catastrophic==0,"catastrophic_benchmark_count":catastrophic,"calibration_regression_policy_passed":bool(evaluable),"conformal_regression_policy_passed":bool(conformal) and all(conformal),"duplicate_suppression_policy_passed":bool(state) and all(m["stateful"]["duplicate_false_suppression_count"]==0 for m in metrics.values() if "stateful" in m)}
    flags["v0312_regression_passed"]=all(flags[k] for k in ("evaluation_coverage_policy_passed","all_absolute_window_gates_passed","all_stateful_gates_passed","all_episode_gates_passed","cross_benchmark_aggregate_policy_passed","non_inferiority_policy_passed","catastrophic_regression_absent","calibration_regression_policy_passed","conformal_regression_policy_passed","duplicate_suppression_policy_passed"))
    return flags,agg

