from __future__ import annotations

import pytest

from collectors.shadow.fault_registry import REGISTRY, UnsupportedFaultScenario, get_scenario
from collectors.shadow.scenario_runner import run_scenario
from collectors.shadow.tests.behavioral_helpers import events


FROZEN_V0314 = [
    "sink_timeout", "sink_unavailable_30s", "sink_unavailable_until_restart", "rate_limit_429",
    "connection_reset_mid_batch", "duplicate_delivery", "duplicate_ack", "out_of_order_ack",
    "malformed_ack", "schema_rejection", "spool_restart", "exporter_crash_after_write_before_ack",
    "exporter_crash_before_write", "queue_80_percent", "queue_95_percent", "queue_full",
    "storage_full_simulated", "clock_forward_jump", "clock_backward_jump", "event_corruption",
    "event_removal", "event_reordering",
]


def test_every_frozen_v0314_scenario_has_explicit_supported_handler():
    assert set(FROZEN_V0314).issubset(REGISTRY)
    assert all(get_scenario(name).supported for name in FROZEN_V0314)


def test_unknown_scenario_never_defaults_to_healthy():
    with pytest.raises(UnsupportedFaultScenario):
        get_scenario("unregistered_fixture")


@pytest.mark.parametrize("scenario", FROZEN_V0314)
def test_frozen_fault_scenario_injects_effect_and_passes_oracle(tmp_path, scenario):
    corpus = events(24)
    result = run_scenario(scenario, tmp_path, corpus)
    assert result["injection_count"] > 0
    assert result["execution_path_differs_from_healthy"]
    assert result["oracle_result"]
    assert result["passed"]
    assert len(result["evidence_sha256"]) == 64


@pytest.mark.parametrize("scenario", ["unknown_ack", "checkpoint_corruption", "spool_corruption", "crash_after_ack_before_checkpoint", "crash_after_checkpoint_before_compaction", "sink_restart", "exporter_restart"])
def test_extended_required_fault_scenario(tmp_path, scenario):
    result = run_scenario(scenario, tmp_path, events(8))
    assert result["passed"]
