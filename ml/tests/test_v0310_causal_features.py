import unittest
from v0310_support import ROOT
from v0310_causal_audit import audit
class TestCausal(unittest.TestCase):
 def test_features(self):self.assertTrue(audit(ROOT/'ml/reports/v0_3_10/test_cf.json',ROOT/'ml/reports/v0_3_10/test_cd.json')[0]['v0310_causal_features_valid'])

