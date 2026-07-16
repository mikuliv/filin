import unittest
from ml.tests._v03101_support import semantics
class TestDedup(unittest.TestCase):
 def test_precision(self):
  m=semantics();self.assertEqual(m["duplicate_alert_suppressed_count"],120);self.assertEqual(m["duplicate_suppression_precision"],1)
