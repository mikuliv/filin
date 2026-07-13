import sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'ml/experiments/v0_3_6'))
from protocol_freeze_audit import freeze
class ProtocolFreezeTests(unittest.TestCase):
 def test_freeze_does_not_load_or_predict(self):
  with tempfile.TemporaryDirectory() as d:
   value=freeze(ROOT/'ml/experiments/v0_3_6/holdout_protocol.yaml',ROOT/'lab/campaigns/v0_3_6_blind_holdout.yaml',ROOT/'ml/experiments/v0_3_6/holdout_evaluation_policy.yaml',ROOT/'ml/experiments/v0_3_4/frozen_candidate_manifest.yaml',Path(d)/'freeze.json')
   self.assertFalse(value['candidate_artifact_loaded']);self.assertFalse(value['prediction_performed'])
