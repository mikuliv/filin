from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "ml" / "analysis"))
from v033_forensic_checks import duplicate_assignment_audit, marker_exclusion_audit, reproduce_aggregation  # noqa: E402


class ForensicEvidenceTests(unittest.TestCase):
    def test_duplicate_assignment_is_counted(self) -> None:
        result = duplicate_assignment_audit([{"event_id": "x", "execution_id": "a", "correlation_status": "assigned"}, {"event_id": "x", "execution_id": "b", "correlation_status": "assigned"}])
        self.assertEqual(result["duplicated_assignments"], 1)

    def test_marker_leak_is_detected(self) -> None:
        event = {"event_id": "marker", "correlation_status": "assigned", "raw": {"uri": "/sensor-marker/start"}}
        self.assertEqual(marker_exclusion_audit([event], {"marker"})["marker_observations_in_features"], 1)

    def test_reproduction_reports_mismatch(self) -> None:
        result = reproduce_aggregation([{"event_id": "x", "execution_id": "a", "correlation_status": "assigned"}], [{"execution_id": "a", "flow_count": 2}], lambda events: {"flow_count": len(events)}, ["flow_count"])
        self.assertEqual(result["aggregation_mismatches"], 1)
