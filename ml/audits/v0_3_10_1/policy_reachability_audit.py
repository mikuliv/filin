"""Логическая достижимость legacy pending gate."""
from __future__ import annotations

def audit(episode_windows: int = 3, maximum_attack_pending_rate: float = 0.20) -> dict:
    if episode_windows < 1: raise ValueError("Episode должен содержать хотя бы одно окно")
    legacy_pending = episode_windows - 1
    legacy_rate = legacy_pending / episode_windows
    burden_rate = 0.0
    incompatible = legacy_rate > maximum_attack_pending_rate
    return {"synthetic_trace_used_as_dataset": False, "episode_windows": episode_windows,
            "first_window_alert_count": 1, "suppressed_continuation_count": legacy_pending,
            "best_case_legacy_attack_pending_rate": legacy_rate, "best_case_burden_pending_rate": burden_rate,
            "maximum_attack_pending_rate": maximum_attack_pending_rate,
            "threshold_reachable_under_legacy_semantics": not incompatible,
            "v0310_pending_policy_structurally_incompatible": incompatible,
            "pending_review_policy_passed_unchanged": False}

