import unittest
from v039_support import ROOT,record
from v039_alert_lifecycle import AlertLifecycle
class TestWeak(unittest.TestCase):
 def test_single_weak_pending(self):
  r=record();r['strong_attack_evidence']=False;r['weak_attack_evidence']=True;life=AlertLifecycle();self.assertTrue(life.update(r)['state_after'].startswith('pending:'))
