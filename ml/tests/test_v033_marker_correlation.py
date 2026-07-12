from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "lab" / "sensor"))
from correlate_sensor_events import correlate  # noqa: E402


class MarkerCorrelationTests(unittest.TestCase):
    def test_marker_flows_are_excluded_and_payload_is_assigned_without_label_matching(self) -> None:
        manifest = {"run_id": "run", "scenarios": [{"run_sequence": 1, "scenario_id": "benign_web_browsing", "label": "benign", "execution_id": "run:1", "scenario_parameter_hash": "a" * 64}]}
        events = [
            {"timestamp": 1.0, "zeek_uid": "start", "raw": {"uri": "/sensor-marker/start/" + "a" * 24}},
            {"timestamp": 2.0, "zeek_uid": "flow", "raw": {"uri": "/index.html"}},
            {"timestamp": 3.0, "zeek_uid": "end", "raw": {"uri": "/sensor-marker/end/" + "a" * 24}},
        ]
        result = correlate(manifest, events)
        self.assertEqual(result[0]["correlation_status"], "excluded")
        self.assertEqual(result[1]["correlation_status"], "assigned")
        self.assertEqual(result[1]["execution_id"], "run:1")
        self.assertEqual(result[2]["correlation_status"], "excluded")

    def test_boundary_after_end_is_background(self) -> None:
        manifest = {"run_id": "run", "scenarios": [{"run_sequence": 1, "scenario_id": "x", "label": "benign", "execution_id": "run:1", "scenario_parameter_hash": "b" * 64}]}
        events = [
            {"timestamp": 1.0, "zeek_uid": "start", "raw": {"uri": "/sensor-marker/start/" + "b" * 24}},
            {"timestamp": 3.0, "zeek_uid": "end", "raw": {"uri": "/sensor-marker/end/" + "b" * 24}},
            {"timestamp": 3.0, "zeek_uid": "later", "raw": {}},
        ]
        self.assertEqual(correlate(manifest, events)[2]["correlation_status"], "background")

