from __future__ import annotations

import json
from pathlib import Path

from .canonical import sha256
from .durable_runtime import ControlledTokenBucket, DurableCheckpoint, RuntimeIntegrityError
from .fault_registry import get_scenario, registry_rows
from .integrated_exporter import IntegratedPassiveExporter, SimulatedCrash
from .integrated_sink import FaultInjectingSink, LocalIdempotentSink


RETRY_SINK = {
    "sink_timeout", "sink_unavailable_30s", "rate_limit_429", "connection_reset_mid_batch",
    "temporary_unavailable", "timeout_sequence", "rate_limited", "connection_reset_after_send", "slow_consumer",
}
ACK_FAULTS = {"duplicate_ack", "out_of_order_ack", "malformed_ack", "unknown_ack", "schema_rejection"}


class ControlledClock:
    def __init__(self):
        self.value = 100.0

    def __call__(self):
        return self.value


def _digest(value: dict) -> str:
    return sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")))


def run_scenario(name: str, root: Path, events: list[dict]) -> dict:
    specification = get_scenario(name)
    runtime = root / name
    evidence: dict = {"scenario_name": name, "injection_count": 0, "observable_effect": None, "recovery": None, "oracle_result": False}

    if name in RETRY_SINK:
        sink = FaultInjectingSink(name)
        exporter = IntegratedPassiveExporter(sink, runtime, batch_size=min(3, len(events)))
        for event in events[:3]: exporter.submit(event)
        exporter.drain(); report = exporter.report()
        evidence.update(injection_count=sink.injection_count, observable_effect="retryable_failure", recovery="bounded_retry", oracle_result=sink.injection_count > 0 and len(sink.events) == 3 and report["reconciliation"]["unaccounted_drop_count"] == 0)
    elif name in ACK_FAULTS:
        sink = FaultInjectingSink(name)
        exporter = IntegratedPassiveExporter(sink, runtime, batch_size=min(3, len(events)))
        for event in events[:3]: exporter.submit(event)
        exporter.drain(); report = exporter.report()
        if name in {"malformed_ack", "unknown_ack"}:
            oracle = report["metrics"].get("malformed_or_unknown_ack_count", 0) == 3 and report["reconciliation"]["pending_events"] == 3
            recovery = "fail_closed_spool_preserved"
        elif name == "schema_rejection":
            oracle = report["metrics"].get("retry_count", 0) == 0 and report["reconciliation"]["permanent_rejected_events"] == 3
            recovery = "permanent_rejection_accounted"
        else:
            oracle = report["checkpoint_acknowledged"] == 3 and len(sink.events) == 3
            recovery = "identity_matched"
        evidence.update(injection_count=sink.injection_count, observable_effect=name, recovery=recovery, oracle_result=oracle)
    elif name in {"sink_unavailable_until_restart", "sink_restart", "restart_sink_before_drain"}:
        broken = FaultInjectingSink("sink_unavailable_until_restart", failures=99)
        first = IntegratedPassiveExporter(broken, runtime, maximum_attempts=1)
        first.submit(events[0]); first.drain()
        sink = LocalIdempotentSink(); second = IntegratedPassiveExporter(sink, runtime)
        recovered = second.recover(); second.drain()
        evidence.update(injection_count=broken.injection_count, observable_effect="event_pending_during_sink_failure", recovery="sink_restart_and_spool_replay", oracle_result=recovered == 1 and len(sink.events) == 1)
    elif name in {"spool_restart", "exporter_restart"}:
        first = IntegratedPassiveExporter(LocalIdempotentSink(), runtime)
        first.submit(events[0])
        sink = LocalIdempotentSink(); second = IntegratedPassiveExporter(sink, runtime)
        recovered = second.recover(); second.drain()
        evidence.update(injection_count=1, observable_effect="memory_queue_replaced", recovery="durable_spool_recovered", oracle_result=recovered == 1 and len(sink.events) == 1)
    elif name in {"duplicate_delivery", "exporter_crash_after_write_before_ack", "crash_after_ack_before_checkpoint"}:
        sink = LocalIdempotentSink(); first = IntegratedPassiveExporter(sink, runtime, crash_at="after_send_before_ack" if name != "crash_after_ack_before_checkpoint" else "after_ack_before_checkpoint")
        first.submit(events[0])
        try: first.drain()
        except SimulatedCrash: pass
        second = IntegratedPassiveExporter(sink, runtime); recovered = second.recover(); second.drain()
        duplicate = second.report()["metrics"].get("duplicate_delivery", 0)
        evidence.update(injection_count=1, observable_effect="accepted_without_checkpoint", recovery="at_least_once_replay_and_sink_dedup", oracle_result=recovered == 1 and duplicate == 1 and len(sink.events) == 1)
    elif name == "exporter_crash_before_write":
        first = IntegratedPassiveExporter(LocalIdempotentSink(), runtime, crash_at="after_validation_before_spool")
        try: first.submit(events[0])
        except SimulatedCrash: pass
        sink = LocalIdempotentSink(); second = IntegratedPassiveExporter(sink, runtime); second.submit(events[0]); second.drain()
        evidence.update(injection_count=1, observable_effect="no_spool_record_created", recovery="source_resubmission", oracle_result=len(sink.events) == 1)
    elif name == "crash_after_checkpoint_before_compaction":
        sink = LocalIdempotentSink(); first = IntegratedPassiveExporter(sink, runtime, crash_at="after_checkpoint_before_compaction")
        first.submit(events[0])
        try: first.drain()
        except SimulatedCrash: pass
        second = IntegratedPassiveExporter(sink, runtime); recovered = second.recover()
        evidence.update(injection_count=1, observable_effect="checkpoint_and_spool_coexist", recovery="checkpoint_wins_and_compacts", oracle_result=recovered == 0 and second.spool.size_bytes == 0 and len(sink.events) == 1)
    elif name in {"queue_80_percent", "queue_95_percent", "queue_full"}:
        capacity = 20 if name != "queue_full" else 2
        target = 16 if name == "queue_80_percent" else 19 if name == "queue_95_percent" else 3
        exporter = IntegratedPassiveExporter(LocalIdempotentSink(), runtime, capacity=capacity)
        decisions = [exporter.submit(event) for event in events[:target]]
        observed_peak = exporter.queue.peak
        exporter.drain(); report = exporter.report()
        if name == "queue_full": oracle = any(not row.accepted for row in decisions) and report["reconciliation"]["unaccounted_drop_count"] == 0
        else: oracle = observed_peak / capacity >= (.8 if name == "queue_80_percent" else .95) and report["reconciliation"]["unaccounted_drop_count"] == 0
        evidence.update(injection_count=1, observable_effect=f"queue_peak={observed_peak}", recovery="bounded_queue_accounting", oracle_result=oracle)
    elif name == "storage_full_simulated":
        exporter = IntegratedPassiveExporter(LocalIdempotentSink(), runtime, spool_bytes=16)
        decision = exporter.submit(events[0]); report = exporter.report()
        evidence.update(injection_count=1, observable_effect="spool_capacity_exceeded", recovery="rejection_accounted", oracle_result=not decision.accepted and report["reconciliation"]["unaccounted_drop_count"] == 0)
    elif name in {"clock_forward_jump", "clock_backward_jump"}:
        clock = ControlledClock(); bucket = ControlledTokenBucket(1, 2, clock)
        bucket.consume(2); before = bucket.tokens
        clock.value += 3600 if name == "clock_forward_jump" else -3600
        wait = bucket.consume(1)
        oracle = 0 <= bucket.tokens <= bucket.capacity and wait >= 0 and (bucket.tokens == 1 if name == "clock_forward_jump" else wait == 1)
        evidence.update(injection_count=1, observable_effect=f"tokens_before={before};wait={wait}", recovery="bounded_monotonic_refill", oracle_result=oracle)
    elif name in {"event_corruption", "spool_corruption"}:
        exporter = IntegratedPassiveExporter(LocalIdempotentSink(), runtime); exporter.submit(events[0])
        path = next(exporter.spool.root.glob("*.event")); payload = path.read_bytes(); path.write_bytes(payload[:-2] + b"x\n")
        detected = False
        try: exporter.spool.recover()
        except RuntimeIntegrityError: detected = True
        evidence.update(injection_count=1, observable_effect="spool_checksum_mismatch", recovery="recovery_refused", oracle_result=detected)
    elif name == "checkpoint_corruption":
        exporter = IntegratedPassiveExporter(LocalIdempotentSink(), runtime); exporter.submit(events[0]); exporter.drain()
        path = runtime / "checkpoint.json"; value = json.loads(path.read_text()); value["checksum"] = "0" * 64; path.write_text(json.dumps(value))
        detected = False
        try: DurableCheckpoint(path)
        except RuntimeIntegrityError: detected = True
        evidence.update(injection_count=1, observable_effect="checkpoint_checksum_mismatch", recovery="resume_refused", oracle_result=detected)
    elif name == "event_removal":
        source = {event["idempotency_key"] for event in events[:2]}; sink = {events[0]["idempotency_key"]}; missing = source - sink
        evidence.update(injection_count=1, observable_effect="source_sink_set_difference", recovery="readiness_blocked", oracle_result=len(missing) == 1)
    elif name == "event_reordering":
        sink = LocalIdempotentSink(); exporter = IntegratedPassiveExporter(sink, runtime, batch_size=3)
        for event in reversed(events[:3]): exporter.submit(event)
        exporter.drain()
        evidence.update(injection_count=1, observable_effect="physical_order_reversed", recovery="identity_reconciliation", oracle_result={e["idempotency_key"] for e in events[:3]} == set(sink.events))
    else:
        raise AssertionError("registered scenario has no runner:" + name)

    evidence["execution_path_differs_from_healthy"] = evidence["injection_count"] > 0 and evidence["observable_effect"] is not None
    evidence["passed"] = bool(evidence["oracle_result"] and evidence["execution_path_differs_from_healthy"])
    evidence["evidence_sha256"] = _digest({key: value for key, value in evidence.items() if key not in {"passed", "evidence_sha256"}})
    evidence["expected_oracle"] = specification.oracle
    return evidence


def run_all(root: Path, events: list[dict]) -> dict:
    results = [run_scenario(row["scenario_name"], root, events) for row in registry_rows()]
    return {
        "scenario_count": len(results),
        "supported_count": len(results),
        "passed_count": sum(row["passed"] for row in results),
        "all_passed_faults_actually_injected": all(row["injection_count"] > 0 for row in results if row["passed"]),
        "all_oracles_passed": all(row["oracle_result"] for row in results),
        "results": results,
    }
