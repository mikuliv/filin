import unittest
from v038_episode_evidence import EpisodeEvidenceAccumulator
class TestEpisodeEvidence(unittest.TestCase):
 def update(self,a,raw,p=.9):return a.update(run_id='r',episode_id='e',raw_state=raw,probabilities={'benign':1-p,'port_scan':p},conformal_p_values={'benign':1-p,'port_scan':p},support_set={'port_scan'} if 'attack_' in raw else {'benign'})
 def test_isolated_spike_not_alert(self):self.assertFalse(self.update(EpisodeEvidenceAccumulator(),'attack_supported:port_scan').startswith('attack_candidate:'))
 def test_two_consistent_promote(self):
  a=EpisodeEvidenceAccumulator();self.update(a,'attack_supported:port_scan');self.assertEqual(self.update(a,'attack_supported:port_scan'),'attack_candidate:port_scan')
 def test_benign_counter_reduces(self):
  a=EpisodeEvidenceAccumulator(policy='signed_decay',activation_threshold=1.2);self.update(a,'attack_supported:port_scan');before=a.scores['port_scan'];self.update(a,'benign_supported',p=.1);self.assertLess(a.scores['port_scan'],before)
