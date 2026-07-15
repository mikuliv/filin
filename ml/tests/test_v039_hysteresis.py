import unittest
from datetime import datetime,timezone,timedelta
from v039_support import ROOT,record
from v039_alert_lifecycle import AlertLifecycle
class TestHysteresis(unittest.TestCase):
 def test_one_benign_does_not_cancel(self):
  life=AlertLifecycle();life.update(record());r=record('benign',.95);self.assertTrue(life.update(r)['state_after'].startswith('active:'))
 def test_two_strong_benign_windows_resolve_after_minimum_hold(self):
  life=AlertLifecycle();life.update(record());self.assertTrue(life.update(record('benign',.95))['state_after'].startswith('active:'));self.assertTrue(life.update(record('benign',.95))['state_after'].startswith('cooldown:'))
 def test_class_replacement_requires_two_confirmations(self):
  life=AlertLifecycle();life.update(record('port_scan'));first=life.update(record('web_probe'));second=life.update(record('web_probe'));self.assertEqual(first['state_after'],'active:port_scan');self.assertEqual(second['state_after'],'active:web_probe')
 def test_inactivity_reset_is_causal(self):
  life=AlertLifecycle(inactivity_seconds=180);life.update(record());later=record();later['timestamp']='2026-01-01T00:03:01+00:00';later['strong_attack_evidence']=False;later['weak_attack_evidence']=False;later['strong_benign_evidence']=False;self.assertEqual(life.update(later)['state_before'],'observing')
