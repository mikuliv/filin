"""Post-hoc promotion funnel для immutable predictions v0.3.10."""
from __future__ import annotations
from collections import Counter

ATTACK_CLASSES = ["port_scan", "auth_failures", "web_probe", "low_rate_dos", "beacon_simulation"]

def analyze(rows, decisions, parameters) -> dict:
    attack_rows = rows.episode_class.ne("benign")
    stages = ["closed_set_correct","top_class_attack","true_class_in_conformal_set","true_class_singleton",
              "strong_probability_pass","strong_margin_pass","strong_benign_ceiling_pass","strong_alert_emitted",
              "weak_probability_pass","weak_margin_pass","pending_created","pending_confirmed","weak_alert_emitted",
              "ambiguous_review","novel_review"]
    values = {name: [] for name in stages}
    for (_, row), decision in zip(rows.iterrows(), decisions.itertuples()):
        if row.episode_class == "benign":
            continue
        label = str(row.episode_class); probabilities = decision.joint_probabilities
        values["closed_set_correct"].append(decision.top_class == label)
        values["top_class_attack"].append(decision.top_class in ATTACK_CLASSES)
        values["true_class_in_conformal_set"].append(label in decision.conformal_set)
        values["true_class_singleton"].append(decision.conformal_set == [label])
        values["strong_probability_pass"].append(probabilities[label] >= parameters["strong_thresholds_per_class"][label])
        values["strong_margin_pass"].append(decision.probability_margin >= parameters["strong_probability_margin"])
        values["strong_benign_ceiling_pass"].append(probabilities["benign"] <= parameters["maximum_strong_benign_probability"])
        values["strong_alert_emitted"].append(decision.final_decision == f"alert_emitted:{label}" and decision.strong_attack_evidence)
        values["weak_probability_pass"].append(probabilities[label] >= parameters["weak_thresholds_per_class"][label])
        values["weak_margin_pass"].append(decision.probability_margin >= parameters["weak_probability_margin"])
        values["pending_created"].append(str(decision.final_decision).startswith("observe_pending:"))
        values["pending_confirmed"].append(bool(decision.pending_record and decision.pending_record.get("confirmation_count",0) >= 2))
        values["weak_alert_emitted"].append(decision.final_decision == f"alert_emitted:{label}" and decision.weak_attack_evidence)
        values["ambiguous_review"].append(decision.final_decision == "review_required:ambiguous")
        values["novel_review"].append(decision.final_decision == "review_required:novel")
    total = int(attack_rows.sum()); report = {}
    previous = total
    for name in stages:
        count = sum(values[name]); report[name] = {"count": count, "rate": count/max(total,1),
            "drop_count": max(previous-count,0), "drop_rate": max(previous-count,0)/max(previous,1)}; previous=count
    unresolved = []
    for episode_id, group in rows[attack_rows].groupby("episode_id", sort=False):
        d = decisions.loc[group.index]
        if not d.final_decision.astype(str).str.startswith("alert_emitted:").any():
            reasons=[]
            if not (d.top_class == group.iloc[0].episode_class).any(): reasons.append("closed_set_top_class_mismatch")
            if not d.conformal_set.map(lambda value: group.iloc[0].episode_class in value).any(): reasons.append("true_class_absent_from_conformal_set")
            if d.final_decision.astype(str).str.startswith("review_required:").any(): reasons.append("ambiguity_or_novel_review")
            if d.final_decision.astype(str).str.startswith("observe_pending:").any(): reasons.append("weak_evidence_not_confirmed")
            if not reasons: reasons.append("probability_or_margin_threshold_not_passed")
            unresolved.append({"episode_id":episode_id,"attack_class":str(group.iloc[0].episode_class),"reasons":reasons})
    return {"attack_window_count":total,"stages":report,"unresolved_episodes":unresolved,
            "unresolved_reason_counts":dict(Counter(reason for item in unresolved for reason in item["reasons"])),
            "validation_used_for_tuning":False}
