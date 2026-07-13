import unittest
from v037_support import *
from v037_temporal_evidence import TemporalEvidenceAccumulator
class TestTemporalEvidence(unittest.TestCase):
 def test_two_of_three_is_causal_and_resets(self):
  a=TemporalEvidenceAccumulator('2_of_3');self.assertFalse(a.update(.9,'a'));self.assertTrue(a.update(.8,'a'));self.assertFalse(a.update(.9,'b'))
