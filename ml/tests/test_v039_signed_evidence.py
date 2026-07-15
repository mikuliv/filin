import unittest
from v039_support import ROOT,record
from v039_signed_evidence import SignedClassEvidence
class TestSigned(unittest.TestCase):
 def test_positive_and_benign_counter(self):self.assertGreater(SignedClassEvidence(.7,1.2).update(record())['port_scan'],0)
