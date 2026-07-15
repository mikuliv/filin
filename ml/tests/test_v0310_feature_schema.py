import unittest
from v0310_support import ROOT
from v0_8_schema_audit import audit
class TestSchema(unittest.TestCase):
 def test_exact_51(self):
  r=audit();self.assertEqual(r['feature_count'],51);self.assertTrue(r['feature_schema_unchanged']);self.assertFalse(r['decision_values_in_X'])

