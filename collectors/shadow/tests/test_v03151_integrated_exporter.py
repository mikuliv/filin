from __future__ import annotations

import pytest

from collectors.shadow.integrated_exporter import IntegratedPassiveExporter, SimulatedCrash
from collectors.shadow.integrated_sink import FaultInjectingSink, LocalIdempotentSink
from collectors.shadow.tests.behavioral_helpers import events


def test_event_spool_queue_rate_sink_ack_checkpoint_compaction(tmp_path):
    corpus = events(12)
    sink = LocalIdempotentSink()
    exporter = IntegratedPassiveExporter(sink, tmp_path, batch_size=4, rate=3)
    assert all(exporter.submit(event).accepted for event in corpus)
    assert exporter.spool.size_bytes > 0
    assert exporter.drain()
    report = exporter.report()
    assert len(sink.events) == len(corpus)
    assert report["checkpoint_acknowledged"] == len(corpus)
    assert report["spool_peak_bytes"] > 0
    assert exporter.spool.size_bytes == 0
    assert report["metrics"]["token_bucket_wait_count"] > 0
    assert report["metrics"]["real_batch_calls"] > 0
    assert report["reconciliation"]["unaccounted_drop_count"] == 0


@pytest.mark.parametrize("scenario", ["sink_timeout", "sink_unavailable_30s", "rate_limit_429", "connection_reset_mid_batch", "slow_consumer"])
def test_retryable_failures_are_retried_and_reconciled(tmp_path, scenario):
    sink = FaultInjectingSink(scenario)
    exporter = IntegratedPassiveExporter(sink, tmp_path / scenario, batch_size=3)
    corpus = events(3)
    for event in corpus:
        exporter.submit(event)
    assert exporter.drain()
    assert sink.injection_count == 1
    assert exporter.report()["metrics"]["retry_count"] == len(corpus)
    assert len(sink.events) == len(corpus)


@pytest.mark.parametrize("scenario", ["malformed_ack", "unknown_ack"])
def test_invalid_ack_is_not_success_and_spool_is_preserved(tmp_path, scenario):
    exporter = IntegratedPassiveExporter(FaultInjectingSink(scenario), tmp_path / scenario)
    exporter.submit(events(1)[0])
    exporter.drain()
    report = exporter.report()
    assert report["checkpoint_acknowledged"] == 0
    assert report["metrics"]["malformed_or_unknown_ack_count"] == 1
    assert report["reconciliation"]["pending_events"] == 1


def test_permanent_rejection_is_not_retried_and_is_accounted(tmp_path):
    sink = FaultInjectingSink("schema_rejection")
    exporter = IntegratedPassiveExporter(sink, tmp_path)
    exporter.submit(events(1)[0])
    assert exporter.drain()
    report = exporter.report()
    assert report["metrics"].get("retry_count", 0) == 0
    assert report["reconciliation"]["permanent_rejected_events"] == 1
    assert report["reconciliation"]["unaccounted_drop_count"] == 0


def test_out_of_order_batch_ack_is_matched_by_identity(tmp_path):
    corpus = events(5)
    exporter = IntegratedPassiveExporter(FaultInjectingSink("out_of_order_ack"), tmp_path, batch_size=5)
    for event in corpus:
        exporter.submit(event)
    assert exporter.drain()
    assert exporter.report()["checkpoint_acknowledged"] == 5


@pytest.mark.parametrize("boundary", sorted(IntegratedPassiveExporter.CRASH_BOUNDARIES))
def test_crash_boundaries_recover_without_semantic_loss(tmp_path, boundary):
    corpus = events(2 if boundary == "during_batch" else 1)
    sink = FaultInjectingSink("sink_timeout") if boundary == "during_retry" else LocalIdempotentSink()
    first = IntegratedPassiveExporter(sink, tmp_path / boundary, batch_size=len(corpus), crash_at=boundary)
    crashed_during_submit = False
    try:
        for event in corpus:
            first.submit(event)
    except SimulatedCrash:
        crashed_during_submit = True
    if not crashed_during_submit:
        with pytest.raises(SimulatedCrash):
            first.drain()
    recovered = IntegratedPassiveExporter(sink, tmp_path / boundary, batch_size=len(corpus))
    count = recovered.recover()
    if boundary == "after_validation_before_spool":
        assert count == 0
        for event in corpus:
            recovered.submit(event)
    assert recovered.drain()
    assert len(sink.events) == len(corpus)
    assert recovered.report()["reconciliation"]["unaccounted_drop_count"] == 0


def test_exporter_restart_recovers_real_spool_and_checkpoint(tmp_path):
    corpus = events(4)
    first = IntegratedPassiveExporter(LocalIdempotentSink(), tmp_path, batch_size=2)
    for event in corpus:
        first.submit(event)
    sink = LocalIdempotentSink()
    second = IntegratedPassiveExporter(sink, tmp_path, batch_size=2)
    assert second.recover() == 4
    assert second.drain()
    assert len(sink.events) == 4
