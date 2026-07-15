import unittest
from v039_support import ROOT,record,probabilities,support,CLASSES
from v039_evidence_record import EvidenceThresholds,build_evidence_record
class TestStrong(unittest.TestCase):
 def test_first_window_and_agreement(self):
  self.assertTrue(record()['strong_attack_evidence']);r=build_evidence_record(timestamp='2026-01-01T00:00:00+00:00',asset_state_key='a',probabilities=probabilities(),conformal_set=['web_probe'],conformal_p_values={x:0 for x in CLASSES},support=support(),thresholds=EvidenceThresholds(.85,.4,1,.1,.45,.8));self.assertFalse(r['strong_attack_evidence'])
 def build(self,values,cset,support_class='port_scan'):
  return build_evidence_record(timestamp='2026-01-01T00:00:00+00:00',asset_state_key='a',probabilities=values,conformal_set=cset,conformal_p_values={x:0 for x in CLASSES},support=support(support_class),thresholds=EvidenceThresholds(.85,.4,1,.1,.45,.8))
 def test_singleton_without_probability_margin_is_not_strong(self):
  values={'port_scan':.46,'web_probe':.44,'benign':.05,'auth_failures':.02,'low_rate_dos':.02,'beacon_simulation':.01};self.assertFalse(self.build(values,['port_scan'])['strong_attack_evidence'])
 def test_support_without_probability_evidence_is_not_strong(self):
  self.assertFalse(self.build(probabilities('port_scan',.60),['port_scan'])['strong_attack_evidence'])
 def test_strong_benign_never_becomes_attack(self):
  result=self.build(probabilities('benign',.95),['benign'],'benign');self.assertTrue(result['strong_benign_evidence']);self.assertFalse(result['strong_attack_evidence'])
 def test_competing_attack_blocks_wrong_strong_subtype(self):
  values={'port_scan':.50,'web_probe':.43,'benign':.02,'auth_failures':.02,'low_rate_dos':.02,'beacon_simulation':.01};self.assertFalse(self.build(values,['port_scan'])['strong_attack_evidence'])
