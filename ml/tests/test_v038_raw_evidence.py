import unittest
from v038_episode_evidence import raw_evidence_state
class TestRawEvidence(unittest.TestCase):
 def test_novel_is_not_attack(self):self.assertEqual(raw_evidence_state({'benign'},set())[0],'unsupported_novel')
 def test_effective_intersection(self):self.assertEqual(raw_evidence_state({'port_scan'},{'port_scan'})[0],'attack_supported:port_scan')
