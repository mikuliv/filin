import unittest
from v0310_support import engine,probabilities
class TestCausal(unittest.TestCase):
 def test_future_does_not_change_first(self):
  e=engine();first=e.decide(activity_state_key='a',window_index=1,probabilities=probabilities(),conformal_set=['port_scan']);e.decide(activity_state_key='a',window_index=2,probabilities=probabilities('benign',.9,.9),conformal_set=['benign']);self.assertEqual(first['final_decision'],'alert_emitted:port_scan')

