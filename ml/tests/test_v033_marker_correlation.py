from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "lab" / "sensor"))
from correlate_sensor_events import correlate, correlate_isolated_capture  # noqa: E402


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

    def test_control_marker_journal_recovers_missing_http_markers(self) -> None:
        nonce = "c" * 24
        manifest = {"run_id": "run", "scenarios": [{"run_sequence": 1, "scenario_id": "x", "label": "benign", "execution_id": "run:1", "scenario_parameter_hash": "c" * 64}]}
        events = [{"timestamp": 2.0, "zeek_uid": "payload", "raw": {"uri": "/api/items"}}]
        controls = [
            {"timestamp": 1.0, "marker_nonce": nonce, "marker_type": "start"},
            {"timestamp": 3.0, "marker_nonce": nonce, "marker_type": "end"},
        ]
        result = correlate(manifest, events, controls)
        self.assertEqual(result[0]["correlation_status"], "assigned")
        self.assertEqual(result[0]["execution_id"], "run:1")

    def test_isolated_capture_assigns_payload_without_wall_clock(self) -> None:
        manifest = {"run_id": "run", "scenarios": [{"run_sequence": 1, "scenario_id": "x", "label": "benign", "execution_id": "run:1"}]}
        events = [
            {"timestamp": 100.0, "zeek_uid": "marker", "raw": {"uri": "/sensor-marker/start/abc"}},
            {"timestamp": 1.0, "zeek_uid": "payload", "raw": {"uri": "/api/items"}},
        ]
        result = correlate_isolated_capture(manifest, events, "run:1")
        self.assertEqual(result[0]["correlation_status"], "excluded")
        self.assertEqual(result[1]["correlation_status"], "assigned")
        self.assertEqual(result[1]["correlation_method"], "isolated_sensor_capture_v1")
