from __future__ import annotations
class Metrics:
    NAMES=("events_generated_total","events_delivered_total","events_retried_total","events_deduplicated_total","events_dropped_total","alerts_generated_total","reviews_generated_total","continuations_aggregated_total","queue_depth","queue_high_watermark_count","spool_bytes","delivery_latency_ms","last_successful_delivery_timestamp","sink_unavailable_seconds","schema_validation_failures_total","privacy_validation_failures_total","automatic_action_attempts_total")
    def __init__(self): self.values={name:0 for name in self.NAMES}
    def inc(self,name,value=1): self.values[name]+=value
    def snapshot(self): return dict(self.values)
