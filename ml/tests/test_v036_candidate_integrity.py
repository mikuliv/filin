import unittest
from ml.tests.v036_test_utils import ROOT,load
from v036_candidate_integrity import audit
class CandidateTests(unittest.TestCase):
 def test_frozen_hash(self):
  result=audit(ROOT/'ml/experiments/v0_3_4/frozen_candidate_manifest.yaml',ROOT/'ml/artifacts/v0_3_4/frozen_candidate.joblib');self.assertTrue(result['v036_candidate_integrity_valid']);self.assertEqual(result['feature_count'],16)
