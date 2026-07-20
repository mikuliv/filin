from __future__ import annotations
from collectors.shadow.in_memory_sink import InMemorySink

def run(events):
    sink=InMemorySink()
    for event in events: sink.send(event)
    for event in events: sink.send(event)
    result={**sink.metrics(),"unique_event_count":len(events),"delivery_semantics":"at_least_once","exactly_once_claimed":False}
    result["idempotency_policy_passed"]=result["sink_unique_event_count"]==result["unique_event_count"] and result["idempotency_collision_count"]==result["semantic_duplicate_count"]==0
    return result
