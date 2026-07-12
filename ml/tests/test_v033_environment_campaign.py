from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "lab" / "campaigns"))

from environment_campaign import build_run_manifest, load_campaign, run_is_complete  # noqa: E402


class EnvironmentCampaignTests(unittest.TestCase):
    def setUp(self) -> None:
        self.campaign = load_campaign(ROOT / "lab" / "campaigns" / "v0_3_3_environment.yaml")

    def test_manifest_has_seventeen_independent_executions(self) -> None:
        manifest = build_run_manifest(self.campaign, self.campaign["runs"][0], ROOT / "lab" / "scenarios")
        self.assertEqual(manifest["scenario_count"], 17)
        self.assertEqual(sum(item["label"] == "benign" for item in manifest["scenarios"]), 12)
        self.assertEqual({item["label"] for item in manifest["scenarios"] if item["label"] != "benign"}, {"port_scan", "auth_failures", "web_probe", "low_rate_dos", "beacon_simulation"})

    def test_execution_ids_and_parameter_hashes_are_deterministic(self) -> None:
        first = build_run_manifest(self.campaign, self.campaign["runs"][0], ROOT / "lab" / "scenarios")
        second = build_run_manifest(self.campaign, self.campaign["runs"][0], ROOT / "lab" / "scenarios")
        self.assertEqual([item["execution_id"] for item in first["scenarios"]], [item["execution_id"] for item in second["scenarios"]])
        self.assertEqual([item["scenario_parameter_hash"] for item in first["scenarios"]], [item["scenario_parameter_hash"] for item in second["scenarios"]])

    def test_success_requires_every_required_phase(self) -> None:
        status = {"run_status": "success", "capture_audit_status": "success", "correlation_audit_status": "success", "aggregation_consistency_status": "success", "sensor_validator_status": "success", "dataset_status": "success"}
        self.assertTrue(run_is_complete(status))
        status["dataset_status"] = "failed"
        self.assertFalse(run_is_complete(status))

