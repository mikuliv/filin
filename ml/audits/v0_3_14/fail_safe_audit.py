from __future__ import annotations

COUNTERS=("automatic_action_attempt_count","network_block_attempt_count","backend_write_attempt_count","production_connection_attempt_count","source_prediction_mutation_count","candidate_artifact_mutation_count","first_alert_lost_count","review_event_lost_count","causal_order_violation_count","unaccounted_drop_count")
def run(extra=None):
    result={name:0 for name in COUNTERS}; result.update(extra or {}); result["fail_safe_policy_passed"]=not any(result[name] for name in COUNTERS); result.update({"automatic_action_absent":result["automatic_action_attempt_count"]==0,"backend_write_absent":result["backend_write_attempt_count"]==0,"production_connection_absent":result["production_connection_attempt_count"]==0}); return result
