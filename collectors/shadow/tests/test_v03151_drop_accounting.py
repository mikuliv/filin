from __future__ import annotations

from collectors.shadow.integrated_exporter import IntegratedPassiveExporter
from collectors.shadow.integrated_sink import LocalIdempotentSink
from collectors.shadow.tests.behavioral_helpers import events


def test_low_priority_eviction_returns_identity_and_reconciles(tmp_path):
    routine, alert = events(2)
    alert = dict(alert)
    alert["event_type"] = "alert_emitted"
    # schema-specific alert fields are required by semantics but not JSON required;
    # hash must be recomputed after the controlled fixture mutation.
    from collectors.shadow.canonical import canonical_bytes, sha256
    alert["event_hash"] = sha256(canonical_bytes(alert))
    exporter = IntegratedPassiveExporter(LocalIdempotentSink(), tmp_path, capacity=1)
    assert exporter.submit(routine).accepted
    decision = exporter.submit(alert)
    assert decision.accepted and decision.evicted["event_id"] == routine["event_id"]
    exporter.drain()
    report = exporter.report()
    assert report["drop_registry"][0]["reason"] == "evicted_low_priority"
    assert report["reconciliation"]["unaccounted_drop_count"] == 0


def test_rejected_enqueue_is_accounted(tmp_path):
    first, second = events(2)
    exporter = IntegratedPassiveExporter(LocalIdempotentSink(), tmp_path, capacity=1)
    exporter.submit(first)
    assert not exporter.submit(second).accepted
    exporter.drain()
    assert exporter.report()["reconciliation"]["unaccounted_drop_count"] == 0
