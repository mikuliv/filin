import ast
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "lab" / "campaigns"))

from run_pre_v038_runtime_smoke import (
    CAPTURE_VOLUME, EXECUTIONS, MGMT_NETWORK, MONITOR_NETWORK, NETWORK, PROJECT, ZEEK_VOLUME, _manifest,
)


class TestPreV038RuntimeSmoke(unittest.TestCase):
    def test_dedicated_compose_namespace_and_volumes(self):
        self.assertTrue(NETWORK.startswith(PROJECT))
        self.assertTrue(MGMT_NETWORK.startswith(PROJECT))
        self.assertTrue(MONITOR_NETWORK.startswith(PROJECT))
        self.assertTrue(CAPTURE_VOLUME.startswith(PROJECT))
        self.assertTrue(ZEEK_VOLUME.startswith(PROJECT))

    def test_manifest_is_future_only_internal_and_label_independent(self):
        manifest = _manifest()
        self.assertEqual(manifest["campaign_role"], "pre_training_smoke")
        self.assertTrue(manifest["capture_dns"])
        self.assertFalse(manifest["network_policy"]["external_dns_allowed"])
        self.assertLessEqual(manifest["marker_reconciliation_policy"]["allowed_capture_jitter_seconds"], 1.5)
        self.assertEqual(len(manifest["scenarios"]), len(EXECUTIONS))
        profiles = {item["environment_profile_id"] for item in manifest["scenarios"]}
        self.assertEqual(profiles, {"no_impairment", "latency_40ms"})
        self.assertEqual(len({item["marker_nonce"] for item in manifest["scenarios"]}), len(EXECUTIONS))
        dns_plan = __import__("future_workflows").WORKFLOW_PLANS["smoke_dns_local_resolution"]
        self.assertEqual([action.target for action in dns_plan], ["target-api", "target-web", "filin-missing-service"])

    def test_runner_has_no_training_or_historical_evaluation_imports(self):
        source = ROOT / "lab" / "campaigns" / "run_pre_v038_runtime_smoke.py"
        tree = ast.parse(source.read_text(encoding="utf-8"))
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.append(node.module or "")
        self.assertFalse(any("training" in name or "v0_3_7" in name or "v036" in name for name in imports))


if __name__ == "__main__":
    unittest.main()
