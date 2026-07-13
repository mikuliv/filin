import unittest
from v037_support import *
from no_fit_guard import NoFitGuard
class TestNoFitGuard(unittest.TestCase):
 def test_fit_and_partial_fit_blocked(self):
  g=NoFitGuard()
  with self.assertRaises(RuntimeError):g.fit([])
  with self.assertRaises(RuntimeError):g.partial_fit([])
  self.assertEqual(g.audit()['fit_call_count'],1);self.assertEqual(g.audit()['partial_fit_call_count'],1)
