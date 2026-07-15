"""Интерпретация оконного evidence после model prediction."""
from __future__ import annotations

from dataclasses import dataclass


ATTACK_CLASSES = ("port_scan", "auth_failures", "web_probe", "low_rate_dos", "beacon_simulation")


@dataclass(frozen=True)
class EvidenceThresholds:
    strong_attack_probability: float
    strong_probability_margin: float
    strong_support_ratio: float
    maximum_strong_benign_probability: float
    weak_attack_probability: float
    benign_strong_probability: float
    benign_support_ratio: float = 1.0
    novelty_threshold: float = 1.25


def build_evidence_record(*, timestamp, asset_state_key, probabilities: dict[str, float], conformal_set,
                          conformal_p_values: dict[str, float], support, thresholds: EvidenceThresholds) -> dict:
    ordered = sorted(probabilities, key=lambda label: (-probabilities[label], label)); top, second = ordered[:2]
    margin = float(probabilities[top] - probabilities[second]); cset = set(conformal_set)
    singleton = len(cset) == 1; singleton_class = next(iter(cset)) if singleton else None
    attack = top in ATTACK_CLASSES
    competing = max((probabilities[name] for name in ATTACK_CLASSES if name != top), default=0.0)
    strong_attack = bool(attack and singleton_class == top and support.best_class == top and
        probabilities[top] >= thresholds.strong_attack_probability and margin >= thresholds.strong_probability_margin and
        support.normalized_distances[top] <= thresholds.strong_support_ratio and
        probabilities["benign"] <= thresholds.maximum_strong_benign_probability and
        probabilities[top] - competing >= thresholds.strong_probability_margin)
    strong_benign = bool(singleton_class == "benign" and top == "benign" and
        probabilities["benign"] >= thresholds.benign_strong_probability and support.ranks["benign"] == 1 and
        support.normalized_distances["benign"] <= thresholds.benign_support_ratio and margin >= thresholds.strong_probability_margin)
    weak_attack = bool(attack and top in cset and support.ranks[top] <= 2 and
        probabilities[top] >= thresholds.weak_attack_probability and margin > 0 and not strong_benign and not strong_attack)
    ambiguous = bool(len(cset) > 1 or (support.best_class != top and min(support.ranks[top], 3) > 1) or margin <= 0)
    novel = bool(not cset or all(value > thresholds.novelty_threshold for value in support.normalized_distances.values()))
    return {"timestamp": timestamp, "asset_state_key": asset_state_key, "joint_probabilities": dict(probabilities),
        "top_class": top, "top_probability": probabilities[top], "second_class": second,
        "second_probability": probabilities[second], "probability_margin": margin,
        "conformal_set": sorted(cset), "conformal_p_values": dict(conformal_p_values),
        "conformal_singleton": singleton, "conformal_top_class": singleton_class,
        "normalized_class_distances": dict(support.normalized_distances), "support_strengths": dict(support.strengths),
        "support_ranks": dict(support.ranks), "support_margins": dict(support.margins),
        "best_support_class": support.best_class, "probability_support_agreement": support.best_class == top,
        "conformal_support_agreement": support.best_class in cset, "strong_benign_evidence": strong_benign,
        "strong_attack_evidence": strong_attack, "weak_attack_evidence": weak_attack,
        "ambiguous_evidence": ambiguous, "novel_evidence": novel, "pending_class": None,
        "active_alert_class": None, "alert_lifecycle_state": "observing"}
