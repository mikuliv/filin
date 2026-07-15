import unittest
from v039_support import ROOT
class TestCausalDecision(unittest.TestCase):
 def test_episode_id_rejected(self):
  from v039_alert_lifecycle import AlertLifecycle
  life=AlertLifecycle();self.assertRaises(ValueError,life.update,{'episode_id':'x'})
