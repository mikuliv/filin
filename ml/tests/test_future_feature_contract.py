import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "ml" / "features"))

from build_future_integrity_dataset import build
from profile_registry import FUTURE_METADATA_COLUMNS, ordered_features, profile_contract
from schema import get_feature_profile
from validators import validate_dataset


PROFILE = "network_sensor_v0_6_integrity"
NONCE = "0123456789abcdef01234567"


def marker(kind, timestamp):
    return {"timestamp": timestamp, "correlation_status": "excluded", "raw": {"uri": f"/sensor-marker/{kind}/{NONCE}"}}


class TestFutureFeatureContract(unittest.TestCase):
    def test_schema_api_delegates_to_single_registry(self):
        self.assertEqual(get_feature_profile(PROFILE), ordered_features(PROFILE))
        contract = profile_contract(PROFILE)
        self.assertEqual(contract["feature_count"], 20)
        self.assertEqual(contract["semantic_version"], "0.6.0")
        self.assertEqual(len(contract["feature_schema_sha256"]), 64)

    def test_dictionary_defines_formula_sources_and_zero_policy(self):
        dictionary = yaml.safe_load((ROOT / "ml" / "features" / "feature_dictionary.yaml").read_text(encoding="utf-8"))
        for definition in dictionary["features"].values():
            self.assertTrue({"formula", "source_fields", "denominator_zero", "unit", "valid_range"} <= set(definition))

    def test_builder_writes_validated_ordered_dataset_and_integrity(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest = {
                "run_id": "future-run", "campaign_id": "future-smoke", "campaign_version": "1",
                "campaign_role": "pre_training_smoke", "campaign_run_index": 1, "campaign_seed": 7,
                "scenarios": [{
                    "execution_id": "exec-001", "marker_nonce": NONCE, "run_sequence": 1,
                    "scenario_id": "smoke-http", "label": "benign", "type": "benign",
                    "scenario_variant_id": "v1", "scenario_parameter_hash": NONCE,
                    "environment_profile_id": "no-impairment",
                }],
            }
            manifest_path = root / "manifest.yaml"
            events_path = root / "events.jsonl"
            output = root / "dataset.csv"
            integrity = root / "integrity.json"
            manifest_path.write_text(yaml.safe_dump(manifest), encoding="utf-8")
            events = [
                marker("start", 10.0), marker("start", 10.1),
                {"timestamp": 11.0, "execution_id": "exec-001", "correlation_status": "assigned", "sensor_log_type": "conn",
                 "raw": {"ts": 11.0, "proto": "tcp", "id.resp_h": "10.0.0.2", "id.resp_p": 80, "service": "http",
                         "duration": 0.2, "orig_bytes": 10, "resp_bytes": 20, "orig_pkts": 1, "resp_pkts": 2, "conn_state": "SF"}},
                marker("end", 14.0), marker("end", 14.1),
            ]
            events_path.write_text("\n".join(json.dumps(item) for item in events), encoding="utf-8")
            evidence = build(manifest_path, events_path, output, integrity_output=integrity)
            validate_dataset(output, kind="windows", feature_profile=PROFILE)
            with output.open(encoding="utf-8", newline="") as source:
                reader = csv.DictReader(source)
                row = next(reader)
                self.assertEqual(reader.fieldnames, [*FUTURE_METADATA_COLUMNS, *ordered_features(PROFILE)])
            self.assertEqual(row["scenario_execution_key"], "future-run:1:smoke-http")
            self.assertEqual(row["execution_mode"], "docker")
            self.assertEqual(row["observation_source"], "network_sensor")
            self.assertNotIn("label", ordered_features(PROFILE))
            self.assertEqual(evidence["status"], "passed")
            self.assertTrue(integrity.is_file())
            for name in ("feature_schema_sha256", "builder_sha256", "dataset_sha256", "row_order_sha256", "execution_mapping_sha256", "marker_intervals_sha256"):
                self.assertEqual(len(evidence[name]), 64)


if __name__ == "__main__":
    unittest.main()
