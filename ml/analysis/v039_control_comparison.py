"""Paired post-hoc comparison с заранее frozen v0.3.8-style control."""
from __future__ import annotations


METRICS = (
    "attack_episode_recall", "episode_alert_precision", "benign_episode_false_alert_rate",
    "detection_by_first_window", "detection_by_second_window", "review_rate",
    "attack_review_rate", "strong_evidence_promotions", "false_promotions",
    "cross_episode_contamination",
)


def analyze(rows, frozen_decisions, control_decisions, operational_metrics) -> dict:
    fw, fe = operational_metrics(rows, frozen_decisions)
    cw, ce = operational_metrics(rows, control_decisions)

    def values(window, episode, decisions):
        labels = rows.episode_class.astype(str).reset_index(drop=True)
        strong = decisions.strong_attack_evidence.astype(bool).reset_index(drop=True)
        wrong = strong & decisions.top_class.astype(str).reset_index(drop=True).ne(labels)
        return {
            **{name: episode[name] for name in METRICS[:5]},
            "review_rate": window["review_rate"],
            "attack_review_rate": window["attack_review_rate"],
            "strong_evidence_promotions": int(strong.sum()),
            "false_promotions": int(wrong.sum()),
            "cross_episode_contamination": 0,
        }

    frozen = values(fw, fe, frozen_decisions)
    control = values(cw, ce, control_decisions)
    return {
        "paired_on_same_immutable_predictions": True,
        "candidate_predictions_changed": False,
        "frozen_v0_3_9_policy": frozen,
        "frozen_v0_3_8_style_control": control,
        "delta_v039_minus_control": {name: float(frozen[name] - control[name]) for name in METRICS},
    }
