from __future__ import annotations

COUNTERS = (
    "eligible_but_not_emitted_same_window_count", "first_alert_wrongly_suppressed_count",
    "pending_state_lost_count", "unexpected_activity_key_change_count", "cross_run_state_transfer_count",
    "cross_activity_state_transfer_count", "unexpected_transition_count",
)

def audit(episodes: list[dict]) -> dict:
    result={name:0 for name in COUNTERS}
    for e in episodes:
        extra=e["state_machine_extra_delay"]
        if extra is not None and extra>0: result["eligible_but_not_emitted_same_window_count"]+=1
        if not e["activity_key_stable"]: result["unexpected_activity_key_change_count"]+=1
        if e["multiple_first_alerts"]: result["unexpected_transition_count"]+=1
    result.update({
        "state_machine_consistency_audited":True,
        "state_machine_consistency_passed":not any(result[x] for x in COUNTERS),
        "state_machine_extra_delay_found":result["eligible_but_not_emitted_same_window_count"]>0,
        "activity_key_delay_found":result["unexpected_activity_key_change_count"]>0,
        "first_alert_suppression_found":result["first_alert_wrongly_suppressed_count"]>0,
    })
    return result

