import unittest
from v039_support import ROOT
class TestEvidenceMetrics(unittest.TestCase):
 def test_required_counts(self):
  t=(ROOT/'ml/experiments/v0_3_9/run_internal_validation.py').read_text(encoding='utf8');self.assertIn('strong_attack_evidence_precision',t);self.assertIn('weak_evidence_precision',t)
