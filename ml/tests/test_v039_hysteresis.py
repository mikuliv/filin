import unittest
from datetime import datetime,timezone,timedelta
from v039_support import ROOT,record
from v039_alert_lifecycle import AlertLifecycle
class TestHysteresis(unittest.TestCase):
 def test_one_benign_does_not_cancel(self):
  life=AlertLifecycle();life.update(record());r=record('benign',.95);self.assertTrue(life.update(r)['state_after'].startswith('active:'))
