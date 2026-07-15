import unittest
from v0310_support import engine,probabilities
class TestAlert(unittest.TestCase):
 def test_immutable_record(self):self.assertEqual(engine().decide(activity_state_key='a',window_index=1,probabilities=probabilities(),conformal_set=['port_scan'])['alert_record']['source_path'],'strong')

