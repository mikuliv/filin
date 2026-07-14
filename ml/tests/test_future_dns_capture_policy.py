import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "lab/tools"))
from scenario_executor import capture_bpf


class TestFutureDnsCapturePolicy(unittest.TestCase):
    def test_historical_capture_filter_is_unchanged(self):
        self.assertEqual(capture_bpf({"campaign_role": "historical"}), ["not", "port", "53"])

    def test_future_internal_smoke_captures_dns(self):
        manifest = {"campaign_role": "pre_training_smoke", "capture_dns": True,
                    "network_policy": {"scope": "internal_docker_only", "external_dns_allowed": False,
                                       "allowed_dns_names": ["target-web", "target-api", "filin-missing-service"]}}
        self.assertEqual(capture_bpf(manifest), [])

    def test_external_or_unregistered_dns_is_rejected(self):
        base = {"campaign_role": "pre_training_smoke", "capture_dns": True,
                "network_policy": {"scope": "internal_docker_only", "external_dns_allowed": False,
                                   "allowed_dns_names": ["example.com"]}}
        with self.assertRaises(ValueError): capture_bpf(base)
        base["network_policy"]["allowed_dns_names"] = ["target-web"]
        base["network_policy"]["external_dns_allowed"] = True
        with self.assertRaises(ValueError): capture_bpf(base)


if __name__ == "__main__": unittest.main()
