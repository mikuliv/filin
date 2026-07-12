from __future__ import annotations

import math
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "ml" / "features"))
from network_sensor_v4 import aggregate_network_sensor_v4  # noqa: E402
from schema import HISTORICAL_V031_BASELINE_FEATURES, NETWORK_SENSOR_V0_3, NETWORK_SENSOR_V0_4, get_feature_profile  # noqa: E402
sys.path.insert(0, str(ROOT / "ml" / "training"))
from v034_feature_contract import select_v034_features  # noqa: E402


def event(log_type: str, raw: dict) -> dict:
    return {"sensor_log_type": log_type, "correlation_status": "assigned", "raw": raw}


class NetworkSensorV4Tests(unittest.TestCase):
    def test_historical_list_is_distinct_from_declared_v3(self) -> None:
        self.assertEqual(HISTORICAL_V031_BASELINE_FEATURES[4:], NETWORK_SENSOR_V0_3)
        self.assertNotEqual(HISTORICAL_V031_BASELINE_FEATURES, NETWORK_SENSOR_V0_3)
        self.assertEqual(get_feature_profile("network_sensor_v0_4"), NETWORK_SENSOR_V0_4)

    def test_exact_zeek_aggregation(self) -> None:
        result = aggregate_network_sensor_v4([
            event("conn", {"ts": 1, "proto": "tcp", "id.resp_h": "10.0.0.2", "id.resp_p": 80, "service": "http", "duration": 2, "orig_bytes": 10, "resp_bytes": 30, "orig_pkts": 1, "resp_pkts": 3, "conn_state": "SF"}),
            event("conn", {"ts": 3, "proto": "udp", "id.resp_h": "10.0.0.3", "id.resp_p": 53, "service": "dns", "duration": 4, "orig_bytes": 20, "resp_bytes": 10, "orig_pkts": 2, "resp_pkts": 1, "conn_state": "REJ"}),
            event("http", {"method": "GET", "status_code": 404, "host": "example", "uri": "/a", "request_body_len": 2, "response_body_len": 4}),
            event("dns", {"query": "example", "answers": ["10.0.0.3"], "rcode_name": "NOERROR"}),
        ])
        self.assertEqual(result["flow_count"], 2.0)
        self.assertEqual(result["flow_duration_median"], 3.0)
        self.assertAlmostEqual(result["flow_duration_std"], 1.0)
        self.assertEqual(result["total_bytes"], 70.0)
        self.assertEqual(result["total_packets"], 7.0)
        self.assertEqual(result["http_4xx_count"], 1.0)
        self.assertEqual(result["dns_success_count"], 1.0)
        self.assertTrue(all(0 <= result[name] <= 1 for name in ("orig_resp_bytes_ratio", "connection_success_rate", "connection_failure_rate", "http_error_rate", "dns_error_rate")))

    def test_one_flow_has_nan_interarrival_statistics(self) -> None:
        result = aggregate_network_sensor_v4([event("conn", {"ts": 1, "proto": "tcp", "conn_state": "SF"})])
        self.assertTrue(math.isnan(result["flow_interarrival_mean"]))
        self.assertTrue(math.isnan(result["flow_duration_std"]))

    def test_feature_contract_rejects_missing_or_metadata(self) -> None:
        import pandas as pd
        with self.assertRaises(ValueError):
            select_v034_features(pd.DataFrame({"run_id": ["x"]}))
