import unittest,yaml
from v0310_support import ROOT
class TestAccess(unittest.TestCase):
 def test_old_roots_and_hashes_denied(self):
  p=yaml.safe_load((ROOT/'ml/experiments/v0_3_10/data_access_policy.yaml').read_text(encoding='utf8'));h=yaml.safe_load((ROOT/p['forbidden_hash_file']).read_text(encoding='utf8'));self.assertTrue(any('v0_3_9' in x for x in p['forbidden_roots']));self.assertGreaterEqual(len(h['hashes']),100)

