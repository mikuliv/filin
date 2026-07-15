import unittest
from v039_support import ROOT
class TestIntegrity(unittest.TestCase):
 def test_hash_before_prediction(self):
  t=(ROOT/'ml/experiments/v0_3_9/run_internal_validation.py').read_text(encoding='utf8');self.assertLess(t.index('gate_artifact_sha256'),t.index('evidence_decisions(rows'))
