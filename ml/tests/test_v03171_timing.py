from __future__ import annotations

import time

from ml.experiments.v0_3_17_1.targeted_trial import (
    COMPONENTS,
    _trace_row,
    classify_mode,
)
from ml.experiments.v0_3_17_1.timing import (
    PHASES,
    latency_breakdown,
    validate_trace_rows,
)


def fixture_rows(
    *,
    clock_domains: tuple[str, str] = ("clock-a", "clock-a"),
    wrong_attempt: bool = False,
    restart: bool = False,
) -> list[dict]:
    rows = []
    parent = None
    base = time.monotonic_ns()
    wall = time.time_ns()
    for index, phase in enumerate(PHASES):
        transport = index >= 7
        attempt = "attempt-1" if transport else None
        if wrong_attempt and phase == "receiver_ack":
            attempt = "attempt-wrong"
        component = COMPONENTS[phase]
        domain = clock_domains[1] if component == "reference-receiver" else clock_domains[0]
        boot = "receiver-boot-2" if restart and component == "reference-receiver" else f"{component}-boot"
        trace_id = f"trace-{index}"
        rows.append(
            _trace_row(
                "event-1",
                trace_id,
                attempt,
                "batch-1" if transport else None,
                component,
                f"process-{component}",
                boot,
                domain,
                phase,
                base + index * 1_000_000,
                wall + index * 1_000_000,
                parent,
            )
        )
        parent = trace_id
    return rows


def test_valid_single_clock_trace() -> None:
    value = validate_trace_rows(fixture_rows())
    assert value["timing_trace_valid"]
    assert value["linear_timestamp_violation_count"] == 0


def test_unattested_multi_clock_trace_fails() -> None:
    value = validate_trace_rows(fixture_rows(clock_domains=("a", "b")))
    assert not value["clock_domain_attestation_passed"]
    assert value["unattested_clock_link_count"] > 0


def test_attested_multi_clock_trace_passes() -> None:
    value = validate_trace_rows(
        fixture_rows(clock_domains=("a", "b")), {("a", "b")}
    )
    assert value["timing_trace_valid"]


def test_wrong_attempt_ack_link_fails() -> None:
    value = validate_trace_rows(fixture_rows(wrong_attempt=True))
    assert value["wrong_attempt_ACK_link_count"] == 2
    assert not value["timing_trace_valid"]


def test_restart_boot_identity_is_explicit_and_valid() -> None:
    rows = fixture_rows(restart=True)
    assert any(row["container_boot_id"] == "receiver-boot-2" for row in rows)
    assert validate_trace_rows(rows)["timing_trace_valid"]


def test_latency_aggregation_uses_healthy_chain() -> None:
    rows = fixture_rows()
    value = latency_breakdown(rows, {"event-1": "healthy_nominal"})
    assert value["healthy_event_count"] == 1
    assert value["fault_event_count"] == 0
    assert value["sensor_to_receiver_p95_ms"] == 8.0


def test_all_required_latency_modes_are_explicit() -> None:
    values = {
        classify_mode("timing_nominal", 0.1, 1, retry=False, slowdown=False),
        classify_mode("timing_nominal", 0.1, 10, retry=False, slowdown=False),
        classify_mode("timing_nominal", 0.1, 20, retry=False, slowdown=False),
        classify_mode("retries_and_restart", 0.2, 1, retry=True, slowdown=False),
        classify_mode("retries_and_restart", 0.51, 1, retry=False, slowdown=False),
        classify_mode("backlog_and_recovery", 0.45, 1, retry=False, slowdown=True),
        classify_mode("backlog_and_recovery", 0.55, 1, retry=False, slowdown=False),
    }
    assert values == {
        "healthy_nominal",
        "elevated",
        "burst",
        "retry",
        "restart",
        "slowdown",
        "recovery",
    }
