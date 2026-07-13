import unittest,yaml
from v037_support import ROOT
class TestDataAccessPolicy(unittest.TestCase):
 def test_policy_freezes_sources_and_known_hashes(self):
  p=yaml.safe_load((ROOT/'ml/experiments/v0_3_7/data_access_policy.yaml').read_text(encoding='utf8'))
  self.assertTrue(p['validation_requires_candidate_freeze']);self.assertEqual(len(p['forbidden_source_sha256']),12);self.assertFalse(p['model_trained_on_v036_data'])
