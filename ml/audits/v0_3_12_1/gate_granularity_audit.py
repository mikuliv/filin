from __future__ import annotations
import math

def audit(attack_episode_count: int, second_window_detected_count: int, frozen_gate: float = .75) -> dict:
    rate = second_window_detected_count / attack_episode_count
    needed = max(0, math.ceil(frozen_gate * attack_episode_count - 1e-12) - second_window_detected_count)
    return {
        "attack_episode_count": attack_episode_count,
        "second_window_detected_count": second_window_detected_count,
        "second_window_detection_rate": rate, "frozen_gate": frozen_gate,
        "absolute_rate_shortfall": max(0., frozen_gate-rate), "episode_increment": 1/attack_episode_count,
        "gate_exactly_achievable": float(frozen_gate*attack_episode_count).is_integer(),
        "minimum_additional_detected_episodes_to_pass": needed,
        "next_achievable_rate": (second_window_detected_count+needed)/attack_episode_count,
        "shortfall_less_than_one_episode_increment": max(0., frozen_gate-rate) < 1/attack_episode_count,
    }

