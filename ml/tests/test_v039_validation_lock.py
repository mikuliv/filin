import unittest
from v039_support import ROOT
class TestLock(unittest.TestCase):
 def test_252_84_288(self):
  t=(ROOT/'ml/analysis/v039_validation_lock_audit.py').read_text(encoding='utf8');self.assertIn('252 rows и 84 episodes',t);self.assertIn('expected_marker_pairs',t);self.assertIn('/"captures"',t);self.assertIn('len(paths) == len(expected) == 48',t)
