import unittest,yaml
from v039_support import ROOT
class TestBalance(unittest.TestCase):
 def test_disjoint_18(self):
  a=yaml.safe_load((ROOT/'lab/scenarios/v0_3_9_training_benign.yaml').read_text(encoding='utf8'))['scenarios'];b=yaml.safe_load((ROOT/'lab/scenarios/v0_3_9_validation_benign.yaml').read_text(encoding='utf8'))['scenarios'];self.assertEqual((len(a),len(b)),(18,18));self.assertFalse({x['scenario_id'] for x in a}&{x['scenario_id'] for x in b})
