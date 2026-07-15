import unittest,yaml
from v0310_support import ROOT
class TestCapture(unittest.TestCase):
 def test_canonical_only(self):
  p=yaml.safe_load((ROOT/'ml/experiments/v0_3_10/capture_lock_policy.yaml').read_text(encoding='utf8'));self.assertEqual(p['canonical_capture_root'],'captures/');self.assertEqual(p['forbidden_fallback_root'],'sensor/')

