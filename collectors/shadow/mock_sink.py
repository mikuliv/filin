from __future__ import annotations
from .in_memory_sink import InMemorySink

class SinkFault(RuntimeError): pass
class MockSink(InMemorySink):
    MODES={"healthy","timeout","temporary_unavailable","rate_limited","malformed_response","duplicate_ack","connection_reset","slow_consumer","storage_full_simulated","schema_reject"}
    def __init__(self,mode="healthy",failures=1): super().__init__(); self.mode=mode; self.failures=failures; self.calls=0
    def send(self,event):
        self.calls+=1
        if self.mode not in self.MODES: raise ValueError("unknown_fault_mode")
        if self.calls<=self.failures and self.mode not in {"healthy","duplicate_ack"}:
            retryable=self.mode not in {"schema_reject","malformed_response"}; raise SinkFault(f"sink_{self.mode}:retryable={str(retryable).lower()}")
        result=super().send(event)
        if self.mode=="duplicate_ack": result["status"]="duplicate_accepted"
        return result
