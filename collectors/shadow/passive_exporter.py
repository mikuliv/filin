from __future__ import annotations
from .queue import BoundedEventQueue
from .retry import backoff_ms
from .observability import Metrics

class PassiveExporter:
    def __init__(self,sink,capacity=2048,retries=5): self.sink=sink; self.queue=BoundedEventQueue(capacity); self.retries=retries; self.metrics=Metrics(); self.retry_count=0; self.fail_safe=False
    def enqueue(self,event):
        accepted=self.queue.put(event); self.metrics.inc("events_generated_total")
        if event["event_type"]=="alert_emitted": self.metrics.inc("alerts_generated_total")
        if event["event_type"]=="review_required": self.metrics.inc("reviews_generated_total")
        if not accepted: self.metrics.inc("events_dropped_total")
        return accepted
    def drain(self):
        while len(self.queue):
            event=self.queue.get(); delivered=False
            for attempt in range(self.retries+1):
                try:
                    ack=self.sink.send(event); delivered=True; self.metrics.inc("events_delivered_total"); self.metrics.inc("events_deduplicated_total",ack["status"]=="duplicate_accepted"); break
                except Exception:
                    if attempt>=self.retries: break
                    self.retry_count+=1; self.metrics.inc("events_retried_total"); backoff_ms(attempt)
            if not delivered: self.fail_safe=True; self.metrics.inc("events_dropped_total")
        return not self.fail_safe
    def graceful_shutdown(self): return self.drain()
    def report(self): return {**self.queue.report(),**self.metrics.snapshot(),"retry_count":self.retry_count,"fail_safe":self.fail_safe,"automatic_action_attempt_count":0,"network_block_attempt_count":0,"backend_write_attempt_count":0,"production_connection_attempt_count":0}
