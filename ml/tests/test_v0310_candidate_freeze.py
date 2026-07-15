import unittest
from v0310_support import ROOT
class TestFreeze(unittest.TestCase):
 def test_runner_freezes_one(self):self.assertIn('frozen_candidate_manifest.yaml',(ROOT/'ml/experiments/v0_3_10/run_nested_decision_selection.py').read_text(encoding='utf8'))

