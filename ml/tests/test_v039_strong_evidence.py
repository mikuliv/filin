import unittest
from v039_support import ROOT,record,probabilities,support,CLASSES
from v039_evidence_record import EvidenceThresholds,build_evidence_record
class TestStrong(unittest.TestCase):
 def test_first_window_and_agreement(self):
  self.assertTrue(record()['strong_attack_evidence']);r=build_evidence_record(timestamp='2026-01-01T00:00:00+00:00',asset_state_key='a',probabilities=probabilities(),conformal_set=['web_probe'],conformal_p_values={x:0 for x in CLASSES},support=support(),thresholds=EvidenceThresholds(.85,.4,1,.1,.45,.8));self.assertFalse(r['strong_attack_evidence'])
