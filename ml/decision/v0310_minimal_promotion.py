"""Минимальный probability-conformal decision layer v0.3.10."""
from __future__ import annotations

import math
from dataclasses import dataclass

from v0310_alert_deduplication import AlertDeduplicator
from v0310_pending_state import PendingState


ATTACK_CLASSES = ["port_scan", "auth_failures", "web_probe", "low_rate_dos", "beacon_simulation"]
CLASSES = ["benign", *ATTACK_CLASSES]


@dataclass(frozen=True)
class MinimalPromotionPolicy:
    strong_thresholds_per_class: dict[str, float]
    strong_probability_margin: float = 0.20
    maximum_strong_benign_probability: float = 0.20
    weak_thresholds_per_class: dict[str, float] | None = None
    weak_probability_margin: float = 0.00
    weak_benign_ceiling: float = 0.50
    weak_repetition_policy: str = "two_of_three"
    pending_ttl_windows: int = 3
    ambiguity_margin: float = 0.07
    strong_benign_probability: float = 0.80
    strong_benign_margin: float = 0.30
    dedup_ttl_windows: int = 3

    def weak_threshold(self, label: str) -> float:
        return float((self.weak_thresholds_per_class or {}).get(label, 0.45))


class MinimalPromotionDecision:
    """Обрабатывает окна строго по порядку, без support, label и episode metadata."""

    def __init__(self, policy: MinimalPromotionPolicy):
        self.policy = policy
        self.pending = PendingState(policy.pending_ttl_windows, policy.weak_repetition_policy)
        self.dedup = AlertDeduplicator(policy.dedup_ttl_windows)

    def reset(self, key: str | None = None) -> None:
        self.pending.reset(key)
        self.dedup.reset(key)

    @staticmethod
    def _ranking(probabilities: dict[str, float]) -> tuple[str, float, float]:
        ordered = sorted(((label, float(probabilities[label])) for label in CLASSES), key=lambda item: (-item[1], CLASSES.index(item[0])))
        return ordered[0][0], ordered[0][1], ordered[0][1] - ordered[1][1]

    def decide(self, *, activity_state_key: str, window_index: int, probabilities: dict[str, float], conformal_set: list[str]) -> dict:
        if set(probabilities) != set(CLASSES) or any(not math.isfinite(float(value)) for value in probabilities.values()):
            return self._result("review_required:novel", None, False, False, False)
        if not conformal_set:
            return self._result("review_required:novel", None, False, False, False)
        if any(label not in CLASSES for label in conformal_set):
            return self._result("review_required:novel", None, False, False, False)
        top, top_probability, margin = self._ranking(probabilities)
        benign_probability = float(probabilities["benign"])

        strong_benign = (top == "benign" and "benign" in conformal_set and
                         benign_probability >= self.policy.strong_benign_probability and
                         margin >= self.policy.strong_benign_margin)
        if strong_benign:
            self.pending.reset(activity_state_key)
            return self._result("benign", None, False, False, True)

        competing = [label for label in ATTACK_CLASSES if label != top and abs(float(probabilities[label]) - top_probability) < self.policy.ambiguity_margin]
        strong = (top in ATTACK_CLASSES and conformal_set == [top] and
                  top_probability >= self.policy.strong_thresholds_per_class[top] and
                  margin >= self.policy.strong_probability_margin and
                  benign_probability <= self.policy.maximum_strong_benign_probability and not competing)
        if strong:
            emitted = self.dedup.emit(activity_state_key, top, window_index, "strong")
            self.pending.reset(activity_state_key)
            state = f"alert_emitted:{top}" if emitted else f"observe_pending:{top}"
            return self._result(state, top, True, False, False, emitted, not bool(emitted), margin, top_probability)

        attack_members = [label for label in conformal_set if label in ATTACK_CLASSES]
        ambiguous = (("benign" in conformal_set and bool(attack_members)) or
                     (len(attack_members) > 1 and margin < self.policy.ambiguity_margin) or
                     bool(competing) or top not in conformal_set)
        if ambiguous:
            return self._result("review_required:ambiguous", top if top in ATTACK_CLASSES else None, False, False, False, margin=margin, probability=top_probability)

        weak = (top in ATTACK_CLASSES and top in conformal_set and
                top_probability >= self.policy.weak_threshold(top) and
                margin >= self.policy.weak_probability_margin and
                benign_probability <= self.policy.weak_benign_ceiling)
        if weak:
            confirmed, pending_record = self.pending.add(activity_state_key, top, window_index, top_probability, margin)
            confirmed_classes = self.pending.confirmed_classes(activity_state_key, window_index)
            if len(confirmed_classes) > 1:
                emitted = self.dedup.emit(activity_state_key, "unclassified", window_index, "unclassified")
                self.pending.reset(activity_state_key)
                state = "alert_emitted:unclassified" if emitted else "review_required:ambiguous"
                return self._result(state, "unclassified", False, True, False, emitted, not bool(emitted), margin, top_probability, pending_record)
            if confirmed:
                emitted = self.dedup.emit(activity_state_key, top, window_index, "weak_repeated")
                self.pending.reset(activity_state_key)
                state = f"alert_emitted:{top}" if emitted else f"observe_pending:{top}"
                return self._result(state, top, False, True, False, emitted, not bool(emitted), margin, top_probability, pending_record)
            return self._result(f"observe_pending:{top}", top, False, True, False, margin=margin, probability=top_probability, pending_record=pending_record)

        self.pending.expire(activity_state_key, window_index)
        if top == "benign" and "benign" in conformal_set:
            return self._result("benign", None, False, False, False, margin=margin, probability=top_probability)
        return self._result("review_required:ambiguous", top if top in ATTACK_CLASSES else None, False, False, False, margin=margin, probability=top_probability)

    @staticmethod
    def _result(state, evidence_class, strong, weak, strong_benign, alert_record=None,
                duplicate_suppressed=False, margin=None, probability=None, pending_record=None):
        return {"final_decision": state, "evidence_class": evidence_class,
                "strong_attack_evidence": bool(strong), "weak_attack_evidence": bool(weak),
                "strong_benign_evidence": bool(strong_benign), "alert_emitted": alert_record is not None,
                "alert_record": alert_record.__dict__ if alert_record else None,
                "duplicate_suppressed": bool(duplicate_suppressed), "probability_margin": margin,
                "top_probability": probability, "pending_record": pending_record.__dict__ if pending_record else None,
                "diagnostic_support_affects_decision": False}

