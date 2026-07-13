from pathlib import Path
import hashlib, unittest, yaml
ROOT=Path(__file__).resolve().parents[2]
class V035PolicyTests(unittest.TestCase):
 def test_policy_is_frozen_and_has_required_gates(self):
  path=ROOT/'ml/experiments/v0_3_5/regression_policy.yaml'; value=yaml.safe_load(path.read_text(encoding='utf-8'))
  self.assertEqual(value['evaluation_policy']['minimum_benign_recall'],.85)
  self.assertTrue(value['integrity_policy']['require_no_fit'])
  self.assertEqual(len(hashlib.sha256(path.read_bytes()).hexdigest()),64)
