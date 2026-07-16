import unittest
from ml.audits.v0_3_10_1.policy_reachability_audit import audit
class TestReachability(unittest.TestCase):
 def test_incompatible(self):
  r=audit();self.assertAlmostEqual(r["best_case_legacy_attack_pending_rate"],2/3);self.assertTrue(r["v0310_pending_policy_structurally_incompatible"])
