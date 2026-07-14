"""Signed episode evidence и operational states v0.3.8."""
from __future__ import annotations

from collections import deque


ATTACK_CLASSES = ["port_scan", "auth_failures", "web_probe", "low_rate_dos", "beacon_simulation"]


def raw_evidence_state(conformal_set: set[str], support_set: set[str]) -> tuple[str, set[str]]:
    if not conformal_set:
        return "empty_conformal_set", set()
    if not support_set:
        return "unsupported_novel", set()
    effective = conformal_set & support_set
    attacks = effective & set(ATTACK_CLASSES)
    if effective == {"benign"}:
        return "benign_supported", effective
    if len(attacks) == 1 and "benign" not in effective:
        return f"attack_supported:{next(iter(attacks))}", effective
    if len(attacks) > 1 and "benign" not in effective:
        return "multiple_attack_supported", effective
    if attacks and "benign" in effective:
        return "benign_attack_ambiguous", effective
    return "weak_probability_evidence", effective


class EpisodeEvidenceAccumulator:
    def __init__(self, policy: str = "hybrid", decay: float = 0.7, activation_threshold: float = 1.6,
                 benign_reset_probability: float = 0.8):
        if policy not in {"consistent_2_of_3", "signed_decay", "hybrid"}:
            raise ValueError("Неизвестная episode policy")
        self.policy = policy
        self.decay = float(decay)
        self.activation_threshold = float(activation_threshold)
        self.benign_reset_probability = float(benign_reset_probability)
        self.run_id = None
        self.episode_id = None
        self.scores = {name: 0.0 for name in ATTACK_CLASSES}
        self.recent = deque(maxlen=3)

    def reset(self, run_id=None, episode_id=None):
        self.run_id, self.episode_id = run_id, episode_id
        self.scores = {name: 0.0 for name in ATTACK_CLASSES}
        self.recent.clear()

    def update(self, *, run_id, episode_id, raw_state: str, probabilities: dict[str, float],
               conformal_p_values: dict[str, float], support_set: set[str]) -> str:
        if self.run_id != run_id or self.episode_id != episode_id:
            self.reset(run_id, episode_id)
        benign_supported = raw_state == "benign_supported" and "benign" in support_set
        benign_counter = probabilities.get("benign", 0.0) * conformal_p_values.get("benign", 0.0) if benign_supported else 0.0
        supported_class = raw_state.split(":", 1)[1] if raw_state.startswith("attack_supported:") else None
        self.recent.append(supported_class)
        active = []
        for label in ATTACK_CLASSES:
            positive = probabilities.get(label, 0.0) * conformal_p_values.get(label, 0.0) if supported_class == label else 0.0
            self.scores[label] = max(0.0, self.decay * self.scores[label] + positive - benign_counter)
            consistent = sum(value == label for value in self.recent) >= 2
            signed = self.scores[label] >= self.activation_threshold
            if (self.policy == "consistent_2_of_3" and consistent) or (self.policy == "signed_decay" and signed) or (self.policy == "hybrid" and (consistent or signed)):
                active.append(label)
        if len(active) == 1 and active[0] in support_set:
            return f"attack_candidate:{active[0]}"
        if active:
            return "suspicious_unclassified"
        if benign_supported and max(self.scores.values()) == 0.0:
            return "benign"
        if raw_state == "unsupported_novel":
            return "review_required:novel"
        if raw_state in {"benign_attack_ambiguous", "multiple_attack_supported"}:
            return "review_required:ambiguous"
        return "review_required:weak_evidence"
