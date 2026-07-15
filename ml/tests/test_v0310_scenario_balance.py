import unittest,yaml
from v0310_support import ROOT
class TestBalance(unittest.TestCase):
 def test_disjoint_catalogs(self):
  a=yaml.safe_load((ROOT/'lab/scenarios/v0_3_10_training_benign.yaml').read_text(encoding='utf8'))['scenarios'];b=yaml.safe_load((ROOT/'lab/scenarios/v0_3_10_validation_benign.yaml').read_text(encoding='utf8'))['scenarios'];self.assertEqual(len(a),16);self.assertEqual(len(b),16);self.assertFalse({x['scenario_id'] for x in a}&{x['scenario_id'] for x in b})

