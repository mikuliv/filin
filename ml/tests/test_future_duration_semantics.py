import sys
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "lab" / "sensor"))
sys.path.insert(0, str(ROOT / "ml" / "features"))

from future_integrity_profile import ORDERED_FEATURES, project_future_row
from marker_intervals import MarkerIntervalError, attach_interval_evidence, resolve_marker_intervals


def source(duration=5.0):
    return {"window_duration_seconds": duration, "window_event_count": 10, "flow_count": 4,
            "tcp_flow_count": 3, "udp_flow_count": 1, "failed_connection_count": 1,
            "total_bytes": 100, "total_packets": 20, "orig_bytes_total": 25,
            "resp_bytes_total": 75, "orig_packets_total": 5, "resp_packets_total": 15,
            "http_request_count": 2, "dns_query_count": 1, "connection_failure_rate": .25,
            "http_error_rate": 0, "dns_error_rate": 0, "unique_destination_ip_count": 2,
            "unique_service_count": 1}


class TestFutureDurationSemantics(unittest.TestCase):
    def setUp(self):
        self.manifest = {"scenarios": [{"execution_id": "e1", "scenario_parameter_hash": "abcdef1234567890abcdef123456", "scenario_id": "s"}]}
        self.events = [
            {"timestamp": 10, "raw": {"uri": "/sensor-marker/start/abcdef1234567890abcdef12"}},
            {"timestamp": 15, "raw": {"uri": "/sensor-marker/end/abcdef1234567890abcdef12"}},
        ]

    def test_marker_interval_defines_duration(self):
        intervals = resolve_marker_intervals(self.manifest, self.events)
        self.assertEqual(intervals["e1"].duration_seconds, 5)

    def test_missing_or_invalid_interval_is_rejected(self):
        with self.assertRaises(MarkerIntervalError): resolve_marker_intervals(self.manifest, [])
        invalid = [dict(self.events[0]), {**self.events[1], "timestamp": 9}]
        with self.assertRaises(MarkerIntervalError): resolve_marker_intervals(self.manifest, invalid)

    def test_no_silent_duration_fallback_and_rates_use_duration(self):
        with self.assertRaises(ValueError): project_future_row({k: v for k, v in source().items() if k != "window_duration_seconds"})
        projected = project_future_row(source(5))
        self.assertEqual(projected["events_per_second"], 2)
        self.assertEqual(projected["bytes_per_second"], 20)

    def test_correct_share_names_and_ordered_contract(self):
        projected = project_future_row(source())
        self.assertEqual(list(projected), ORDERED_FEATURES)
        self.assertEqual(projected["orig_bytes_share"], .25)
        self.assertNotIn("orig_resp_bytes_ratio", projected)

    def test_assigned_event_receives_interval_evidence(self):
        intervals = resolve_marker_intervals(self.manifest, self.events)
        attached = attach_interval_evidence([{"execution_id": "e1", "correlation_status": "assigned"}], intervals)[0]
        self.assertEqual(attached["correlation_interval_duration_seconds"], 5)

    def test_dictionary_covers_exact_contract(self):
        dictionary = yaml.safe_load((ROOT / "ml/features/feature_dictionary.yaml").read_text(encoding="utf-8"))
        self.assertEqual(dictionary["ordered_features"], ORDERED_FEATURES)
        self.assertEqual(set(dictionary["features"]), set(ORDERED_FEATURES))
        for entry in dictionary["features"].values():
            self.assertTrue({"description", "unit", "valid_range", "source", "missing", "empty_window"} <= set(entry))


if __name__ == "__main__": unittest.main()
