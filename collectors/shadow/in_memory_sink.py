from __future__ import annotations
from .schema_validator import validate

class InMemorySink:
    def __init__(self): self.events={}; self.attempts=0; self.duplicates=0
    def send(self,event):
        self.attempts+=1; validate(event)
        key=event["idempotency_key"]
        if key in self.events:
            if self.events[key]["event_hash"]!=event["event_hash"]: raise ValueError("idempotency_collision")
            self.duplicates+=1; return {"status":"duplicate_accepted","event_id":event["event_id"]}
        self.events[key]=dict(event); return {"status":"accepted","event_id":event["event_id"]}
    def metrics(self): return {"delivery_attempt_count":self.attempts,"duplicate_delivery_count":self.duplicates,"sink_unique_event_count":len(self.events),"idempotency_collision_count":0,"semantic_duplicate_count":0}
