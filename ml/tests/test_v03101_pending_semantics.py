import unittest
from ml.tests._v03101_support import semantics
class TestPendingSemantics(unittest.TestCase):
 def test_legacy(self):
  m=semantics();self.assertEqual(m["legacy_pending_count"],120);self.assertAlmostEqual(m["legacy_pending_rate"],.37037037037037035)
