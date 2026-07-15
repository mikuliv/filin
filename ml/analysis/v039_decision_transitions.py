"""Post-hoc классификация причинных decision transitions v0.3.9."""
from __future__ import annotations

from collections import Counter


TRANSITION_CLASSES = (
    "closed_correct_strong_promotion", "closed_correct_pending", "closed_correct_review",
    "closed_correct_false_alert", "closed_wrong_recovered_by_evidence",
    "closed_wrong_recovered_by_episode", "closed_wrong_false_alert",
    "strong_attack_promoted_first_window", "weak_attack_confirmed_second_window",
    "weak_attack_confirmed_third_window", "isolated_attack_like_benign_suppressed",
    "pending_reset_by_benign", "pending_expired", "active_alert_preserved",
    "active_alert_resolved", "class_conflict_unclassified", "cross_episode_contamination",
)


def _classify(row, decision) -> str:
    truth = str(row.episode_class)
    top = str(decision.top_class)
    final = str(decision.final_decision)
    before, after = str(decision.state_before), str(decision.state_after)
    phase = str(row.episode_phase)
    active = final.startswith("active:")
    if before.startswith("active:") and after.startswith("active:"):
        return "active_alert_preserved"
    if before.startswith("active:") and not after.startswith("active:"):
        return "active_alert_resolved"
    if after == "active:unclassified":
        return "class_conflict_unclassified"
    if before.startswith("pending:") and after == "observing":
        return "pending_reset_by_benign" if truth == "benign" else "pending_expired"
    if truth == "benign" and bool(decision.weak_attack_evidence) and not active:
        return "isolated_attack_like_benign_suppressed"
    if truth != "benign" and bool(decision.strong_attack_evidence) and active and phase == "phase_1":
        return "strong_attack_promoted_first_window"
    if truth != "benign" and bool(decision.weak_attack_evidence) and active:
        return "weak_attack_confirmed_second_window" if phase == "phase_2" else "weak_attack_confirmed_third_window"
    if top == truth:
        if bool(decision.strong_attack_evidence) and active:
            return "closed_correct_strong_promotion"
        if after.startswith("pending:"):
            return "closed_correct_pending"
        if final.startswith("review:"):
            return "closed_correct_review"
        return "closed_correct_false_alert" if truth == "benign" and active else "closed_correct_pending"
    if active and final == f"active:{truth}":
        return "closed_wrong_recovered_by_evidence"
    if active:
        return "closed_wrong_false_alert"
    return "closed_wrong_recovered_by_episode"


def analyze(rows, decisions, serialized_rows: list[dict]) -> dict:
    classes = [_classify(row, decision) for row, decision in zip(rows.itertuples(), decisions.itertuples())]
    records = []
    for payload, transition_class in zip(serialized_rows, classes):
        records.append({**payload, "transition_class": transition_class})
    counts = Counter(classes)
    return {
        "transition_taxonomy": list(TRANSITION_CLASSES),
        "transition_counts": {name: int(counts.get(name, 0)) for name in TRANSITION_CLASSES},
        "unclassified_transition_count": 0,
        "cross_episode_contamination_count": int(counts.get("cross_episode_contamination", 0)),
        "rows": records,
    }
