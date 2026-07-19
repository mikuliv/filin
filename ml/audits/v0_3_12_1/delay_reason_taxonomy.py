from __future__ import annotations

TAXONOMY = (
    "top_class_is_benign", "top_class_is_wrong_attack", "top_class_changed_since_previous_window",
    "true_class_not_top1", "conformal_empty", "conformal_multi_class", "conformal_wrong_singleton",
    "conformal_true_class_missing", "conformal_not_attack_singleton", "strong_probability_below_threshold",
    "strong_margin_below_threshold", "strong_benign_ceiling_failed", "strong_class_mismatch",
    "strong_not_eligible", "weak_probability_below_threshold", "weak_margin_below_threshold",
    "weak_benign_ceiling_failed", "weak_conformal_conflict", "weak_class_instability",
    "weak_first_observation_only", "weak_repetition_not_confirmed", "weak_not_eligible",
    "activity_key_changed", "activity_key_missing", "pending_state_not_carried", "pending_reset",
    "pending_expired", "review_ambiguous", "review_novel", "review_class_conflict",
    "dedup_active_before_first_alert", "unexpected_state_transition", "alert_already_emitted",
    "post_alert_continuation", "alert_eligible_and_emitted",
)

PRIMARY_PRECEDENCE = (
    "input_or_mapping_error", "activity_key_error", "unexpected_state_transition",
    "top_class_is_benign", "top_class_is_wrong_attack", "conformal_empty", "conformal_multi_class",
    "conformal_true_class_missing", "strong_benign_ceiling_failed", "strong_probability_below_threshold",
    "strong_margin_below_threshold", "weak_conformal_conflict", "weak_benign_ceiling_failed",
    "weak_probability_below_threshold", "weak_margin_below_threshold", "weak_class_instability",
    "weak_repetition_not_confirmed", "review_state", "other_frozen_gate", "no_additional_blocker",
)

def primary_reason(blockers: list[str]) -> str:
    mapped = set(blockers)
    if any(x.startswith("activity_key_") for x in mapped): mapped.add("activity_key_error")
    if any(x.startswith("review_") for x in mapped): mapped.add("review_state")
    for reason in PRIMARY_PRECEDENCE:
        if reason in mapped:
            return reason
    return "other_frozen_gate" if blockers else "no_additional_blocker"

