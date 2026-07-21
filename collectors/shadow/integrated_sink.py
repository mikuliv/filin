from __future__ import annotations

from .acknowledgement import make_ack
from .schema_validator import validate


class TransportFailure(RuntimeError):
    def __init__(self, error_class: str, retryable: bool = True):
        super().__init__(error_class)
        self.error_class = error_class
        self.retryable = retryable


class LocalIdempotentSink:
    def __init__(self):
        self.events: dict[str, dict] = {}
        self.attempts = 0
        self.batch_calls = 0
        self.sequence = 0

    def send(self, event: dict) -> dict:
        return self.send_batch([event])[0]

    def send_batch(self, events: list[dict]) -> list[dict]:
        self.batch_calls += 1
        acknowledgements = []
        for event in events:
            self.attempts += 1
            validate(event)
            key = event["idempotency_key"]
            if key in self.events:
                if self.events[key]["event_hash"] != event["event_hash"]:
                    acknowledgements.append(make_ack(event, "rejected_permanent", "invalid_contract", sequence=self.sequence))
                else:
                    acknowledgements.append(make_ack(event, "duplicate", sequence=self.sequence))
                continue
            self.sequence += 1
            self.events[key] = dict(event)
            acknowledgements.append(make_ack(event, sequence=self.sequence))
        return acknowledgements


class FaultInjectingSink(LocalIdempotentSink):
    def __init__(self, scenario: str, failures: int = 1):
        super().__init__()
        self.scenario = scenario
        self.failures = failures
        self.injection_count = 0

    def send_batch(self, events: list[dict]) -> list[dict]:
        if self.injection_count < self.failures:
            self.injection_count += 1
            first = events[0]
            if self.scenario in {"sink_timeout", "timeout_sequence"}:
                raise TransportFailure("timeout")
            if self.scenario in {"sink_unavailable_30s", "sink_unavailable_until_restart", "temporary_unavailable", "restart_sink_before_drain"}:
                raise TransportFailure("sink_unavailable")
            if self.scenario in {"connection_reset_mid_batch", "connection_reset_after_send"}:
                if self.scenario == "connection_reset_after_send":
                    super().send_batch(events)
                raise TransportFailure("connection_reset")
            if self.scenario in {"rate_limit_429", "rate_limited"}:
                return [make_ack(item, "rate_limited", "rate_limit", retry_after_ms=1) for item in events]
            if self.scenario == "slow_consumer":
                return [make_ack(item, "rejected_temporary", "slow_consumer") for item in events]
            if self.scenario in {"malformed_ack", "malformed_response"}:
                return [{"status": "accepted"} for _ in events]
            if self.scenario == "unknown_ack":
                return [make_ack(item) | {"status": "mystery"} for item in events]
            if self.scenario == "schema_rejection":
                return [make_ack(item, "rejected_permanent", "schema_rejection") for item in events]
            if self.scenario == "authentication_failure":
                return [make_ack(item, "rejected_permanent", "authentication") for item in events]
            if self.scenario == "authorization_failure":
                return [make_ack(item, "rejected_permanent", "authorization") for item in events]
            if self.scenario == "duplicate_ack":
                result = super().send_batch(events)
                return [make_ack(item, "duplicate", sequence=self.sequence) for item in events]
            if self.scenario == "out_of_order_ack":
                return list(reversed(super().send_batch(events)))
        return super().send_batch(events)
