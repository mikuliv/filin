import unittest,yaml
from v0310_support import ROOT
class TestProtocol(unittest.TestCase):
 def test_contract(self):
  p=yaml.safe_load((ROOT/'ml/experiments/v0_3_10/protocol.yaml').read_text(encoding='utf8'));self.assertEqual(p['base_architecture']['architecture_id'],'network_sensor_v0_8_minimal_promotion');self.assertEqual(len(p['seeds']),18);self.assertTrue(p['constraints']['validation_capture_lock_required_before_prediction'])

