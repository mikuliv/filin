import unittest
from v038_support import ROOT
class TestCandidateIntegrity(unittest.TestCase):
 def test_hash_checked_before_prediction(self):self.assertIn('Candidate artifact hash mismatch',(ROOT/'ml/experiments/v0_3_8/run_internal_validation.py').read_text(encoding='utf8'))
