from __future__ import annotations

from dataclasses import asdict, dataclass


class UnsupportedFaultScenario(ValueError):
    pass


@dataclass(frozen=True)
class FaultScenario:
    scenario_name: str
    injector: str
    trigger_condition: str
    expected_effect: str
    expected_recovery: str
    oracle: str
    supported: bool = True


def _scenario(name, injector, effect, recovery, oracle):
    return FaultScenario(name, injector, "first eligible runtime operation", effect, recovery, oracle)


_ROWS = [
    _scenario("sink_timeout", "sink", "timeout", "bounded retry and delivery", "injection>0 and retry>0 and reconciled"),
    _scenario("sink_unavailable_30s", "sink", "temporary unavailable", "bounded retry and delivery", "injection>0 and reconciled"),
    _scenario("sink_unavailable_until_restart", "sink_restart", "unavailable", "new sink and replay spool", "pending before restart and reconciled after restart"),
    _scenario("rate_limit_429", "ack", "rate limited ACK", "Retry-After and delivery", "validated retryable ACK and reconciled"),
    _scenario("connection_reset_mid_batch", "sink", "connection reset", "at-least-once batch retry", "injection>0 and reconciled"),
    _scenario("duplicate_delivery", "transport", "same event delivered twice", "sink deduplication", "duplicate ACK and one sink event"),
    _scenario("duplicate_ack", "ack", "duplicate ACK", "accept as idempotent success", "strict ACK validation succeeds"),
    _scenario("out_of_order_ack", "ack", "ACK order differs", "match by idempotency key", "all batch members checkpointed"),
    _scenario("malformed_ack", "ack", "incomplete ACK", "fail closed and preserve spool", "ACK failure counted and event pending"),
    _scenario("schema_rejection", "ack", "permanent rejection", "no retry", "one permanent attempt and accounted rejection"),
    _scenario("spool_restart", "exporter_restart", "queued memory lost", "recover durable spool", "recovered count and reconciled"),
    _scenario("exporter_crash_after_write_before_ack", "crash", "crash after durable write", "recover spool and deliver", "pending durable event then reconciled"),
    _scenario("exporter_crash_before_write", "crash", "crash before durable write", "caller resubmits source event", "no false checkpoint and eventual delivery"),
    _scenario("queue_80_percent", "queue", "high watermark", "continue bounded operation", "observed depth >=80% and no unaccounted drop"),
    _scenario("queue_95_percent", "queue", "critical watermark", "continue bounded operation", "observed depth >=95% and no unaccounted drop"),
    _scenario("queue_full", "queue", "enqueue rejection or priority eviction", "account exact decision", "drop registry reconciles"),
    _scenario("storage_full_simulated", "spool", "capacity rejection", "account rejection without loss claim", "spool full observed and reconciled"),
    _scenario("clock_forward_jump", "clock", "token refill bounded by capacity", "continue delivery", "no negative wait or unbounded tokens"),
    _scenario("clock_backward_jump", "clock", "negative elapsed clamped", "continue delivery", "no token creation from backward jump"),
    _scenario("event_corruption", "spool", "checksum mismatch", "reject/quarantine", "integrity error observed"),
    _scenario("event_removal", "reconciliation", "source event absent from sink", "detect mismatch", "unaccounted count becomes nonzero"),
    _scenario("event_reordering", "batch", "physical order changed", "identity-based ACK matching", "all events checkpointed"),
    _scenario("unknown_ack", "ack", "unknown status", "fail closed and preserve spool", "unknown ACK counted and pending"),
    _scenario("checkpoint_corruption", "checkpoint", "checksum mismatch", "refuse recovery", "integrity error observed"),
    _scenario("spool_corruption", "spool", "checksum mismatch", "refuse recovery", "integrity error observed"),
    _scenario("crash_after_ack_before_checkpoint", "crash", "sink accepted but checkpoint absent", "duplicate delivery and sink dedup", "duplicate ACK and reconciled"),
    _scenario("crash_after_checkpoint_before_compaction", "crash", "checkpoint and spool coexist", "skip acknowledged record and compact", "no repeated semantic event"),
    _scenario("sink_restart", "sink_restart", "volatile transport interruption", "spool replay", "eventual reconciliation"),
    _scenario("exporter_restart", "exporter_restart", "in-memory queue loss", "spool recovery", "eventual reconciliation"),
]

REGISTRY = {row.scenario_name: row for row in _ROWS}


def get_scenario(name: str) -> FaultScenario:
    try:
        return REGISTRY[name]
    except KeyError as exc:
        raise UnsupportedFaultScenario(f"unsupported_fault_scenario:{name}") from exc


def registry_rows() -> list[dict]:
    return [{**asdict(row), "evidence_artifacts": []} for row in _ROWS]
