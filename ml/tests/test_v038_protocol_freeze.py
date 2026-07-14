import tempfile,unittest
from pathlib import Path
from v038_support import ROOT,load_v038
audit=load_v038('v038_protocol_freeze_unique','ml/experiments/v0_3_8/protocol_freeze_audit.py').audit
class TestProtocolFreeze(unittest.TestCase):
 def test_all_hashes_frozen(self):
  with tempfile.TemporaryDirectory() as d:
   result=audit(ROOT/'ml/experiments/v0_3_8/protocol.yaml',Path(d)/'audit.json')
  self.assertTrue(result['v038_protocol_frozen_before_training']);self.assertIn('validation_policy_sha256',result)
