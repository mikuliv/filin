from __future__ import annotations

import json

import pytest

from collectors.shadow.privacy import audit_targets, sanitize_exception, validate
from collectors.shadow.tests.behavioral_helpers import events


TARGETS = [
    "canonical_event_objects", "canonical_serialized_events", "spool_files", "spool_indexes", "retry_journal",
    "delivery_logs", "health_events", "queue_diagnostics", "drop_summaries", "checkpoint",
    "acknowledgement_records", "error_reports", "exception_messages", "fault_injection_records",
    "performance_traces", "bundle_reports",
]


def test_all_frozen_privacy_targets_are_scanned():
    event = events(1)[0]
    safe = {name: {"event_id": event["event_id"], "status": "safe"} for name in TARGETS}
    safe["canonical_event_objects"] = event
    safe["canonical_serialized_events"] = json.dumps(event, sort_keys=True)
    result = audit_targets(safe)
    assert result["targets"] == sorted(TARGETS)
    assert result["finding_count"] == 0


@pytest.mark.parametrize("fixture", [
    {"message": "192.0.2.10"}, {"message": "00:11:22:33:44:55"}, {"hostname": "workstation.local"},
    {"username": "fixture-user"}, {"message": "user@example.test"}, {"message": "https://example.test/a?q=secret"},
    {"cookie": "session=x"}, {"authorization": "Bearer abc"}, {"message": "api_key=fixture-secret"},
    {"password": "fixture"}, {"payload": "raw"}, {"feature_vector": [1, 2]}, {"label": "attack"},
    {"message": "C:\\Users\\fixture\\secret.txt"},
])
def test_sensitive_negative_fixtures_are_rejected(fixture):
    with pytest.raises(ValueError): validate(fixture)


def test_exception_sanitization_does_not_copy_sensitive_message():
    value = sanitize_exception(RuntimeError("Bearer secret-token user@example.test"))
    assert "secret-token" not in json.dumps(value)
    assert "example.test" not in json.dumps(value)
