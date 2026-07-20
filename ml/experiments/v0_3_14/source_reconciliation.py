from __future__ import annotations
from collections import Counter

def reconcile(records,events):
    states=Counter(row["primary_state"].split(":",1)[0] for row in records); types=Counter(event["event_type"] for event in events); mapping=Counter(event["source_row_id"] for event in events)
    alert_rows={row["immutable_row_id"] for row in records if row["primary_state"].startswith("alert_emitted:")}; review_rows={row["immutable_row_id"] for row in records if row["primary_state"].startswith("review_required:")}
    alert_events={event["source_row_id"] for event in events if event["event_type"]=="alert_emitted"}; review_events={event["source_row_id"] for event in events if event["event_type"]=="review_required"}
    passed=len(records)==700 and states["alert_emitted"]==124 and states["post_alert_continuation"]==212 and states["review_required"]==12 and types["decision_observation"]==700 and alert_rows==alert_events and review_rows==review_events and all(value>=1 for value in mapping.values())
    return {"source_row_count":len(records),"source_state_counts":dict(states),"generated_event_counts":dict(types),"mapped_source_row_count":len(mapping),"minimum_source_event_mapping_count":min(mapping.values()),"maximum_source_event_mapping_count":max(mapping.values()),"missing_alert_events":len(alert_rows-alert_events),"missing_review_events":len(review_rows-review_events),"event_without_source_count":sum(event["source_row_id"] not in {r["immutable_row_id"] for r in records} for event in events),"source_event_reconciliation_passed":passed}
