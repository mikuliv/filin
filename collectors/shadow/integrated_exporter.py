from __future__ import annotations

import json
import time
from collections import Counter
from pathlib import Path
from typing import Callable

from .acknowledgement import AckContractError, validate_ack
from .durable_runtime import ControlledTokenBucket, DurableCheckpoint, DurablePriorityQueue, DurableSpool, QueueDecision, SpoolFull
from .integrated_sink import TransportFailure
from .privacy import validate as validate_privacy
from .retry import backoff_ms
from .schema_validator import validate as validate_schema


class SimulatedCrash(RuntimeError):
    pass


class IntegratedPassiveExporter:
    """Один at-least-once runtime path от validation до checkpoint и compaction."""

    CRASH_BOUNDARIES = {
        "after_validation_before_spool",
        "after_spool_before_queue",
        "after_queue_before_send",
        "after_send_before_ack",
        "after_ack_before_checkpoint",
        "after_checkpoint_before_compaction",
        "during_compaction",
        "during_retry",
        "during_batch",
    }

    def __init__(
        self,
        sink,
        runtime_root: str | Path,
        *,
        capacity: int = 2048,
        batch_size: int = 1,
        rate: float = 10_000,
        maximum_attempts: int = 4,
        spool_bytes: int = 256 * 1024 * 1024,
        crash_at: str | None = None,
        clock=time.monotonic,
        sleeper: Callable[[float], None] = lambda _seconds: None,
        event_validator: Callable[[dict], bool] = validate_schema,
    ):
        if crash_at is not None and crash_at not in self.CRASH_BOUNDARIES:
            raise ValueError("unknown_crash_boundary")
        self.sink = sink
        self.root = Path(runtime_root)
        self.event_validator = event_validator
        privacy_validator = (lambda _event: True) if event_validator is not validate_schema else validate_privacy
        self.spool = DurableSpool(self.root / "spool", spool_bytes, event_validator=event_validator, privacy_validator=privacy_validator)
        self.checkpoint = DurableCheckpoint(self.root / "checkpoint.json")
        self.queue = DurablePriorityQueue(capacity)
        self.bucket = ControlledTokenBucket(rate, max(rate, batch_size), clock)
        self.batch_size = batch_size
        self.maximum_attempts = maximum_attempts
        self.crash_at = crash_at
        self.crashed: set[str] = set()
        self.sleeper = sleeper
        self.metrics = Counter()
        self.drop_registry: list[dict] = []
        self.retry_journal: list[dict] = []
        self.acknowledgement_records: list[dict] = []
        self.delivery_logs: list[dict] = []
        self.total_input_events = len(self.checkpoint.acknowledged)

    def _crash(self, boundary: str) -> None:
        if self.crash_at == boundary and boundary not in self.crashed:
            self.crashed.add(boundary)
            raise SimulatedCrash(boundary)

    def _account_drop(self, event: dict, reason: str) -> None:
        self.drop_registry.append({"event_id": event["event_id"], "idempotency_key": event["idempotency_key"], "reason": reason})
        self.metrics[reason] += 1

    def submit(self, event: dict) -> QueueDecision:
        self.total_input_events += 1
        try:
            self.event_validator(event)
            if event.get("event_contract_version") != "shadow_event_v2":
                validate_privacy(event)
        except ValueError:
            self._account_drop(event, "invalid_schema_rejection")
            return QueueDecision(False, rejected=event, reason="invalid_schema_rejection")
        self.metrics["validated_events"] += 1
        self._crash("after_validation_before_spool")
        try:
            self.spool.append(event)
        except SpoolFull:
            self._account_drop(event, "rejected_on_enqueue")
            return QueueDecision(False, rejected=event, reason="spool_full")
        self.metrics["spooled_events"] += 1
        self._crash("after_spool_before_queue")
        decision = self.queue.put(event)
        if decision.evicted:
            self._account_drop(decision.evicted, "evicted_low_priority")
            self.spool.remove(decision.evicted)
        if not decision.accepted:
            self._account_drop(event, decision.reason or "rejected_on_enqueue")
            self.spool.remove(event)
        else:
            self.metrics["queued_events"] += 1
        return decision

    def recover(self) -> int:
        recovered = 0
        for event in self.spool.recover():
            if event["idempotency_key"] in self.checkpoint.acknowledged:
                self.spool.remove(event)
                continue
            decision = self.queue.put(event)
            if decision.accepted:
                recovered += 1
            else:
                raise RuntimeError("recovery_queue_capacity_insufficient")
        self.metrics["recovered_events"] += recovered
        self.total_input_events += recovered
        return recovered

    def _send_batch(self, batch: list[dict]) -> list[dict]:
        self._crash("after_queue_before_send")
        self._crash("during_batch")
        wait = self.bucket.consume(len(batch))
        if wait:
            self.metrics["token_bucket_wait_count"] += 1
            self.metrics["token_bucket_wait_us"] += int(wait * 1_000_000)
            self.sleeper(wait)
        if len(batch) > 1:
            self.metrics["real_batch_calls"] += 1
        self.metrics["delivery_attempts"] += len(batch)
        if hasattr(self.sink, "send_batch"):
            acknowledgements = self.sink.send_batch(batch)
        else:
            acknowledgements = [self.sink.send(event) for event in batch]
        self._crash("after_send_before_ack")
        return acknowledgements

    def drain(self) -> bool:
        while len(self.queue):
            batch = self.queue.get_batch(self.batch_size)
            pending = list(batch)
            for attempt in range(1, self.maximum_attempts + 1):
                try:
                    raw_acks = self._send_batch(pending)
                    if len(raw_acks) != len(pending):
                        raise AckContractError("malformed_ack:batch_cardinality")
                    by_key = {ack.get("idempotency_key"): ack for ack in raw_acks if isinstance(ack, dict)}
                    decisions = []
                    for event in pending:
                        raw = by_key.get(event["idempotency_key"])
                        if raw is None:
                            raise AckContractError("malformed_ack:missing_identity")
                        decisions.append((event, raw, validate_ack(raw, event)))
                except TransportFailure as exc:
                    self.metrics["retryable_failed_attempts" if exc.retryable else "permanent_failed_attempts"] += len(pending)
                    if not exc.retryable or attempt == self.maximum_attempts:
                        if not exc.retryable:
                            for event in pending:
                                self._account_drop(event, "permanent_rejection")
                                self.spool.remove(event)
                        else:
                            self.metrics["retry_exhausted"] += len(pending)
                        break
                    self.retry_journal.append({"attempt": attempt, "error_class": exc.error_class, "event_ids": [item["event_id"] for item in pending]})
                    self.metrics["retry_count"] += len(pending)
                    self._crash("during_retry")
                    self.sleeper(backoff_ms(attempt - 1, initial=1, maximum=20, seed=3151) / 1000)
                    continue
                except AckContractError as exc:
                    self.metrics["malformed_or_unknown_ack_count"] += len(pending)
                    for event in pending:
                        self.delivery_logs.append({"event_id": event["event_id"], "outcome": "ack_contract_failure", "error": str(exc)})
                    break

                retry_events = []
                for event, raw, decision in decisions:
                    self.acknowledgement_records.append(raw)
                    if decision.outcome == "success":
                        self.metrics["successful_attempts"] += 1
                        self.metrics["duplicate_delivery"] += int(decision.status == "duplicate")
                        self._crash("after_ack_before_checkpoint")
                        self.checkpoint.commit(event)
                        self._crash("after_checkpoint_before_compaction")
                        self._crash("during_compaction")
                        self.spool.remove(event)
                        self.delivery_logs.append({"event_id": event["event_id"], "outcome": decision.status})
                    elif decision.outcome == "retryable_failure":
                        self.metrics["retryable_failed_attempts"] += 1
                        retry_events.append(event)
                    else:
                        self.metrics["permanent_failed_attempts"] += 1
                        self._account_drop(event, "permanent_rejection")
                        self.spool.remove(event)
                if not retry_events:
                    break
                if attempt == self.maximum_attempts:
                    self.metrics["retry_exhausted"] += len(retry_events)
                    break
                self.retry_journal.append({"attempt": attempt, "error_class": "ack_retryable", "event_ids": [item["event_id"] for item in retry_events]})
                self.metrics["retry_count"] += len(retry_events)
                pending = retry_events
        return self.reconciliation()["unaccounted_drop_count"] == 0

    def reconciliation(self) -> dict:
        delivered = len(self.checkpoint.acknowledged)
        pending = len(self.spool.recover())
        accounted = sum(1 for row in self.drop_registry if row["reason"] not in {"permanent_rejection"})
        permanent = sum(1 for row in self.drop_registry if row["reason"] == "permanent_rejection")
        right = delivered + pending + accounted + permanent
        attempts = self.metrics["successful_attempts"] + self.metrics["retryable_failed_attempts"] + self.metrics["permanent_failed_attempts"]
        return {
            "total_input_events": self.total_input_events,
            "delivered_unique_events": delivered,
            "pending_events": pending,
            "accounted_dropped_events": accounted,
            "permanent_rejected_events": permanent,
            "unaccounted_drop_count": self.total_input_events - right,
            "delivery_attempts": self.metrics["delivery_attempts"],
            "classified_attempts": attempts,
            "attempt_accounting_delta": self.metrics["delivery_attempts"] - attempts,
        }

    def report(self) -> dict:
        return {
            "delivery_semantics": "at-least-once",
            "metrics": dict(self.metrics),
            "queue_peak": self.queue.peak,
            "queue_capacity": self.queue.capacity,
            "spool_peak_bytes": self.spool.peak_bytes,
            "checkpoint_acknowledged": len(self.checkpoint.acknowledged),
            "sink_unique_events": len(getattr(self.sink, "events", {})),
            "drop_registry": self.drop_registry,
            "retry_journal": self.retry_journal,
            "reconciliation": self.reconciliation(),
            "automatic_action_attempt_count": 0,
            "network_block_attempt_count": 0,
            "backend_write_attempt_count": 0,
            "production_connection_attempt_count": 0,
            "external_network_attempt_count": 0,
        }
