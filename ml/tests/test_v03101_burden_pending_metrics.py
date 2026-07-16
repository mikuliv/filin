import unittest
from ml.tests._v03101_support import semantics
class TestBurden(unittest.TestCase):
 def test_zero(self):
  m=semantics();self.assertEqual(m["burden_pending_count"],0);self.assertEqual(m["attack_burden_pending_rate"],0)
