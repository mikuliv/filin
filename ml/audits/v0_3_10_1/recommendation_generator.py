"""Рекомендации, не меняющие frozen policy."""
from __future__ import annotations

def generate() -> dict:
    return {"recommendations_are_frozen_policy": False,
            "operational_states": ["benign", "pre_alert_pending:<class>", "alert_emitted:<class>",
                "post_alert_continuation:<class>", "duplicate_alert_suppressed:<class>",
                "review_required:ambiguous", "review_required:novel", "unresolved_pending:<class>"],
            "future_policy_gates": ["maximum_pre_alert_pending_rate", "maximum_unresolved_pending_episode_rate",
                "maximum_review_rate", "minimum_duplicate_suppression_precision", "maximum_duplicate_false_suppression_rate",
                "minimum_attack_episode_recall", "minimum_episode_alert_precision"],
            "post_alert_continuation_is_pending_burden": False,
            "duplicate_suppression_is_missed_detection": False,
            "persistent_alert_for_window_metrics": False}
