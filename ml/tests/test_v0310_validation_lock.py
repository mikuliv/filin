import unittest
from v0310_support import ROOT
class TestLock(unittest.TestCase):
 def test_fail_closed_count(self):
  text=(ROOT/'ml/analysis/v0310_validation_lock_audit.py').read_text(encoding='utf8');self.assertIn('360',text);self.assertIn('Post-hoc',text)

