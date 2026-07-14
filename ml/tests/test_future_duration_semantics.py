import unittest
from pathlib import Path
import sys

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "lab/sensor")); sys.path.insert(0, str(ROOT / "ml/features"))
from future_integrity_profile import ORDERED_FEATURES, project_future_row
from marker_intervals import MarkerIntervalError, attach_interval_evidence, marker_interval_set_sha256, resolve_marker_intervals

NONCE = "abcdef1234567890abcdef12"


def manifest(count=1):
    return {"scenarios": [{"execution_id": f"e{i}", "marker_nonce": NONCE if i == 0 else f"nonce{i:019d}", "scenario_id": f"s{i}"} for i in range(count)]}


def event(kind, timestamp, nonce=NONCE, status="excluded"):
    return {"timestamp": timestamp, "correlation_status": status, "raw": {"uri": f"/sensor-marker/{kind}/{nonce}"}}


def source(duration=5.0):
    return {"window_duration_seconds": duration, "window_event_count": 10, "flow_count": 4,
            "tcp_flow_count": 3, "udp_flow_count": 1, "failed_connection_count": 1,
            "total_bytes": 100, "total_packets": 20, "orig_bytes_total": 25,
            "resp_bytes_total": 75, "orig_packets_total": 5, "resp_packets_total": 15,
            "http_request_count": 2, "dns_query_count": 1, "connection_failure_rate": .25,
            "http_error_rate": 0, "dns_error_rate": 0, "unique_destination_ip_count": 2,
            "unique_service_count": 1}


class TestFutureDurationSemantics(unittest.TestCase):
    def test_one_pair(self):
        interval = resolve_marker_intervals(manifest(), [event("start", 10), event("end", 15)])["e0"]
        self.assertEqual(interval.duration_seconds, 5); self.assertEqual(interval.sensor_start_count, 1)

    def test_two_and_five_copies_choose_last_start_first_end(self):
        for copies in (2, 5):
            events = [event("start", 10 + i * .2) for i in range(copies)] + [event("end", 20 + i * .2) for i in range(copies)]
            interval = resolve_marker_intervals(manifest(), events)["e0"]
            self.assertAlmostEqual(interval.start, 10 + (copies - 1) * .2); self.assertEqual(interval.end, 20)
            self.assertEqual(interval.sensor_start_count, copies); self.assertEqual(interval.sensor_end_count, copies)

    def test_lost_copy_still_resolves(self):
        interval = resolve_marker_intervals(manifest(), [event("start", 10), event("end", 20), event("end", 20.2)])["e0"]
        self.assertEqual((interval.sensor_start_count, interval.sensor_end_count), (1, 2))

    def test_control_only_and_combined_evidence(self):
        controls = [{"marker_nonce": NONCE, "marker_type": "start", "timestamp": 10.3}, {"marker_nonce": NONCE, "marker_type": "end", "timestamp": 19.9}]
        control = resolve_marker_intervals(manifest(), [], controls)["e0"]
        self.assertEqual(control.sensor_control_reconciliation, "control_only")
        combined = resolve_marker_intervals(manifest(), [event("start", 10), event("start", 10.2), event("end", 20)], controls)["e0"]
        self.assertEqual(combined.sensor_control_reconciliation, "agreed")

    def test_disagreement_unknown_type_and_duplicate_nonce_fail(self):
        controls = [{"marker_nonce": NONCE, "marker_type": "start", "timestamp": 30}, {"marker_nonce": NONCE, "marker_type": "end", "timestamp": 40}]
        with self.assertRaises(MarkerIntervalError): resolve_marker_intervals(manifest(), [event("start", 10), event("end", 20)], controls)
        with self.assertRaises(MarkerIntervalError): resolve_marker_intervals(manifest(), [event("middle", 10)])
        duplicate = {"scenarios": [{"execution_id": "a", "marker_nonce": NONCE}, {"execution_id": "b", "marker_nonce": NONCE}]}
        with self.assertRaises(MarkerIntervalError): resolve_marker_intervals(duplicate, [])

    def test_negative_and_overlapping_intervals_fail(self):
        with self.assertRaises(MarkerIntervalError): resolve_marker_intervals(manifest(), [event("start", 20), event("end", 10)])
        second = "nonce0000000000000000002"
        values = [event("start", 10), event("end", 20), event("start", 15, second), event("end", 25, second)]
        with self.assertRaises(MarkerIntervalError): resolve_marker_intervals(manifest(2), values)

    def test_marker_flows_never_enter_features(self):
        intervals = resolve_marker_intervals(manifest(), [event("start", 10), event("end", 20)])
        with self.assertRaises(MarkerIntervalError): attach_interval_evidence([{"execution_id": "e0", **event("start", 10, status="assigned")}], intervals)

    def test_canonical_hash_is_deterministic(self):
        intervals = resolve_marker_intervals(manifest(), [event("start", 10), event("end", 20)])
        self.assertEqual(marker_interval_set_sha256(intervals), marker_interval_set_sha256(intervals))
        self.assertEqual(len(marker_interval_set_sha256(intervals)), 64)

    def test_no_duration_fallback_and_rates_use_duration(self):
        with self.assertRaises(ValueError): project_future_row({k: v for k, v in source().items() if k != "window_duration_seconds"})
        projected = project_future_row(source(5)); self.assertEqual(projected["events_per_second"], 2); self.assertEqual(projected["bytes_per_second"], 20)

    def test_correct_share_names_order_and_dictionary(self):
        projected = project_future_row(source()); self.assertEqual(list(projected), ORDERED_FEATURES)
        self.assertEqual(projected["orig_bytes_share"], .25); self.assertNotIn("orig_resp_bytes_ratio", projected)
        dictionary = yaml.safe_load((ROOT / "ml/features/feature_dictionary.yaml").read_text(encoding="utf-8"))
        self.assertEqual(dictionary["ordered_features"], ORDERED_FEATURES); self.assertEqual(set(dictionary["features"]), set(ORDERED_FEATURES))


if __name__ == "__main__": unittest.main()
