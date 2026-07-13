import unittest
class NoFitGuardTests(unittest.TestCase):
 def test_policy_explicitly_requires_no_fit(self):
  import yaml
  from pathlib import Path
  p=Path(__file__).resolve().parents[2]/'ml/experiments/v0_3_5/regression_policy.yaml'
  self.assertTrue(yaml.safe_load(p.read_text())['integrity_policy']['require_no_fit'])
