import tempfile,unittest
from pathlib import Path
from v039_support import ROOT
from v039_condition_independence_audit import audit
class TestCondition(unittest.TestCase):
 def test_valid(self):
  with tempfile.TemporaryDirectory() as d:self.assertTrue(audit(ROOT/'lab/campaigns/v0_3_9_training.yaml',ROOT/'lab/campaigns/v0_3_9_internal_validation.yaml',Path(d)/'a.json')['v039_condition_independence_valid'])
