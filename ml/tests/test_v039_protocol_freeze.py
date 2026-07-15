import unittest,yaml
from v039_support import ROOT
class TestProtocol(unittest.TestCase):
 def test_all_inputs_frozen(self):
  p=yaml.safe_load((ROOT/'ml/experiments/v0_3_9/protocol.yaml').read_text(encoding='utf8'));self.assertEqual(p['base_architecture']['feature_count'],51);self.assertTrue(p['constraints']['candidate_frozen_before_validation_collection']);self.assertEqual(len(p['seeds']),18)
