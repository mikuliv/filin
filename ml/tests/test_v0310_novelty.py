import unittest
from v0310_support import engine,probabilities
class TestNovel(unittest.TestCase):
 def test_empty_set(self):self.assertEqual(engine().decide(activity_state_key='a',window_index=1,probabilities=probabilities(),conformal_set=[])['final_decision'],'review_required:novel')

