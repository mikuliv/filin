from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator

from ml.experiments.v0_3_17_1.forensic import (
    REPORT,
)


ROOT = Path(__file__).resolve().parents[2]


def test_all_ten_historical_mismatches_are_resolved_without_mutation() -> None:
    value = json.loads(
        (REPORT / "historical_anchor_root_cause_report.json").read_text(
            encoding="utf-8"
        )
    )
    assert value["historical_anchor_mismatch_count"] == 10
    assert value["historical_anchor_resolved_count"] == 10
    assert value["unresolved_historical_anchor_count"] == 0
    assert value["confirmed_historical_mutation_count"] == 0
    assert all(not row["historical_file_modified"] for row in value["anchors"])
    assert all(row["diagnostics"]["canonical_git_objects_equal"] for row in value["anchors"])


def test_all_historical_timestamp_violations_are_classified() -> None:
    value = json.loads(
        (REPORT / "clock_domain_root_cause_report.json").read_text(encoding="utf-8")
    )
    linkage = json.loads(
        (REPORT / "trace_linkage_report.json").read_text(encoding="utf-8")
    )
    counts = value["classification_counts"]
    assert value["reported_linear_timestamp_violation_count"] == 69806
    assert sum(counts.values()) == 69806
    assert counts["field_order_error"] == 640
    assert counts["invalid_trace_fixture"] == 69166
    assert linkage["historical_linkage_attestable"] is False


def test_duplicate_counter_uses_actual_event_references() -> None:
    value = json.loads(
        (REPORT / "transport_duplicate_semantics_report.json").read_text(
            encoding="utf-8"
        )
    )
    assert value["reported_transport_duplicate_count"] == 436080
    assert value["duplicate_batch_attempt_count"] == 6
    assert value["duplicate_event_delivery_attempt_count"] == 280
    assert value["counter_double_counting_count"] == 435800
    assert value["transport_duplicate_semantics_resolved"]


def test_timing_trace_v2_schema_accepts_complete_row() -> None:
    schema = json.loads(
        (ROOT / "rehearsal/contracts/runtime_timing_trace_v2.schema.json").read_text(
            encoding="utf-8"
        )
    )
    row = {
        "trace_contract_version": "runtime_timing_trace_v2",
        "event_id": "evt-1",
        "trace_id": "trace-1",
        "attempt_id": "attempt-1",
        "batch_id": "batch-1",
        "component_id": "connector",
        "process_instance_id": "process-1",
        "container_boot_id": "boot-1",
        "clock_domain_id": "clock-1",
        "timestamp_name": "send_started",
        "monotonic_ns": 100,
        "wall_clock_ns": 200,
        "parent_trace_ref": "trace-parent",
    }
    Draft202012Validator(schema).validate(row)


def test_reports_contain_no_absolute_drive_paths() -> None:
    for path in REPORT.glob("*.json"):
        text = path.read_text(encoding="utf-8")
        assert "G:\\" not in text
        assert "H:\\" not in text
