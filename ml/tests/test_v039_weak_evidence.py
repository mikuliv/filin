import unittest
from v039_support import ROOT,record
from v039_alert_lifecycle import AlertLifecycle
class TestWeak(unittest.TestCase):
 def test_single_weak_pending(self):
  r=record();r['strong_attack_evidence']=False;r['weak_attack_evidence']=True;life=AlertLifecycle();self.assertTrue(life.update(r)['state_after'].startswith('pending:'))
 def weak(self,top='port_scan'):
  r=record(top);r['strong_attack_evidence']=False;r['weak_attack_evidence']=True;return r
 def test_two_consistent_weak_windows_activate(self):
  life=AlertLifecycle();life.update(self.weak());self.assertEqual(life.update(self.weak())['state_after'],'active:port_scan')
 def test_inconsistent_weak_classes_do_not_activate_wrong_subtype(self):
  life=AlertLifecycle();life.update(self.weak('port_scan'));self.assertFalse(life.update(self.weak('web_probe'))['state_after'].startswith('active:'))
 def test_strong_benign_resets_pending(self):
  life=AlertLifecycle();life.update(self.weak());self.assertEqual(life.update(record('benign',.95))['state_after'],'observing')
 def test_pending_expires_at_ttl(self):
  life=AlertLifecycle(state_ttl_windows=3);life.update(self.weak());neutral=self.weak();neutral['weak_attack_evidence']=False
  life.update(neutral);life.update(neutral);self.assertEqual(life.update(neutral)['state_after'],'observing')
