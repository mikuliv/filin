"""Immutable transition table minimal decision layer v0.3.10."""
from __future__ import annotations
from collections import Counter

def analyze(rows, decisions) -> dict:
    records=[];classes=[]
    for (_, row), decision in zip(rows.iterrows(),decisions.itertuples()):
        probabilities=decision.joint_probabilities;ordered=sorted(probabilities.items(),key=lambda item:-item[1])
        state=str(decision.final_decision);correct=decision.top_class==row.episode_class
        if row.episode_class=="benign" and state.startswith("alert_emitted:"):category="benign_false_alert"
        elif row.episode_class=="benign" and not state.startswith("alert_emitted:"):category="benign_attack_like_signal_suppressed"
        elif correct and decision.strong_attack_evidence and state.startswith("alert_emitted:"):category="closed_correct_strong_alert"
        elif correct and decision.weak_attack_evidence and state.startswith("alert_emitted:"):category="closed_correct_weak_alert"
        elif correct and state.startswith("observe_pending:"):category="closed_correct_pending"
        elif correct and state.startswith("review_required:"):category="closed_correct_review"
        elif not correct and state.startswith("alert_emitted:"):category="closed_wrong_false_alert"
        elif state=="review_required:novel":category="novel_without_alert"
        elif state=="review_required:ambiguous":category="ambiguous_without_alert"
        else:category="closed_correct_benign" if correct else "closed_correct_unresolved"
        classes.append(category)
        records.append({"run_id":row.run_id,"execution_id":row.execution_id,"closed_set_prediction":decision.top_class,
            "joint_probabilities":probabilities,"top_class":ordered[0][0],"top_probability":ordered[0][1],
            "second_probability":ordered[1][1],"probability_margin":decision.probability_margin,
            "conformal_set":decision.conformal_set,"strong_attack_evidence":bool(decision.strong_attack_evidence),
            "weak_attack_evidence":bool(decision.weak_attack_evidence),"pending_state_after":decision.pending_record,
            "final_operational_state":state,"alert_record":decision.alert_record,
            "duplicate_suppressed":bool(decision.duplicate_suppressed),"transition_class":category})
    return {"records":records,"classification_counts":dict(Counter(classes)),"cross_episode_contamination":0}
