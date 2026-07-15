import unittest
from v039_support import ROOT,record
from v039_alert_lifecycle import AlertLifecycle
class TestLifecycle(unittest.TestCase):
 def test_strong_activates(self):self.assertEqual(AlertLifecycle().update(record())['state_after'],'active:port_scan')
