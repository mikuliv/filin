import importlib.util
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CLIENT = ROOT / "lab/docker/services/traffic-client"
sys.path.insert(0, str(CLIENT))
from future_workflows import WORKFLOW_PLANS, behavioral_fingerprint


class TestFutureBenignWorkflows(unittest.TestCase):
    def test_every_future_plan_has_distinct_behavioral_fingerprint(self):
        fingerprints = [behavioral_fingerprint(name) for name in WORKFLOW_PLANS]
        self.assertEqual(len(fingerprints), len(set(fingerprints)))

    def test_dns_workflows_create_dns_observations(self):
        for name in ("benign_dns_failover_rotation", "benign_multi_resolver_discovery", "benign_dns_cache_repopulation", "benign_resolver_failover_cycle"):
            self.assertTrue(any(action.kind == "dns" for action in WORKFLOW_PLANS[name]))

    def test_websocket_is_not_a_plain_get(self):
        for name in ("benign_websocket_keepalive", "benign_websocket_session_recovery", "benign_long_poll_reconnect"):
            self.assertTrue(any(action.kind == "websocket" for action in WORKFLOW_PLANS[name]))
            self.assertFalse(all(action.kind == "http" and action.operation.startswith("GET:") for action in WORKFLOW_PLANS[name]))

    def test_plans_are_bounded_and_local(self):
        allowed = {"target-web", "target-api", "control-api", "internal-dns", "target-ssh-sim"}
        for plan in WORKFLOW_PLANS.values():
            self.assertLessEqual(len(plan), 5)
            self.assertTrue(all(action.target in allowed for action in plan))


if __name__ == "__main__": unittest.main()
