import unittest
from v039_support import ROOT,record
from v039_alert_lifecycle import AlertLifecycle
class TestContamination(unittest.TestCase):
 def test_run_reset(self):
  life=AlertLifecycle();life.update(record());life.reset_run();self.assertFalse(life.states)
