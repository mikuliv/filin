import unittest
from v0310_support import engine,probabilities
class TestAmbiguity(unittest.TestCase):
 def test_review(self):self.assertEqual(engine().decide(activity_state_key='a',window_index=1,probabilities=probabilities(),conformal_set=['benign','port_scan'])['final_decision'],'review_required:ambiguous')

