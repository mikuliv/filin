import unittest
from v0310_support import engine,probabilities
class TestWeak(unittest.TestCase):
 def test_two_confirm(self):
  e=engine();p=probabilities('port_scan',.6,.2);self.assertTrue(e.decide(activity_state_key='a',window_index=1,probabilities=p,conformal_set=['port_scan'])['final_decision'].startswith('observe_pending:'));self.assertEqual(e.decide(activity_state_key='a',window_index=2,probabilities=p,conformal_set=['port_scan'])['final_decision'],'alert_emitted:port_scan')

