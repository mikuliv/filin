import unittest
from ml.audits.v0_3_10_1.training_selection_audit import policy_gates
from ml.tests._v03101_support import load
class TestReview(unittest.TestCase):
 def test_split_gates_exist(self):
  record=load("ml/reports/v0_3_10/candidate_selection.json")["selected"]
  gates=policy_gates(record,load("ml/reports/v0_3_10/closed_set_metrics.json"),{"burden_pending_rate":0,"attack_burden_pending_rate":0})
  self.assertIn("review",gates);self.assertIn("burden_pending",gates);self.assertIn("legacy_pending",gates)
