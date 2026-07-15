import unittest
from v0310_support import engine,probabilities
class TestSupport(unittest.TestCase):
 def test_not_input(self):
  r=engine().decide(activity_state_key='a',window_index=1,probabilities=probabilities(),conformal_set=['port_scan']);self.assertFalse(r['diagnostic_support_affects_decision'])

