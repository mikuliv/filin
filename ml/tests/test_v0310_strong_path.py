import unittest
from v0310_support import engine,probabilities
class TestStrong(unittest.TestCase):
 def test_singleton_alert(self):self.assertEqual(engine().decide(activity_state_key='a',window_index=1,probabilities=probabilities(),conformal_set=['port_scan'])['final_decision'],'alert_emitted:port_scan')
 def test_no_singleton_no_strong(self):self.assertFalse(engine().decide(activity_state_key='a',window_index=1,probabilities=probabilities(),conformal_set=['port_scan','web_probe'])['strong_attack_evidence'])

