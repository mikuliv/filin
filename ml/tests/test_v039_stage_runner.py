import unittest
from v039_support import ROOT
class TestStage(unittest.TestCase):
 def test_resume_skips_irreversible(self):
  t=(ROOT/'ml/experiments/v0_3_9/run_v0_3_9_stage.py').read_text(encoding='utf8');self.assertIn('if not state.get("grouped_oof")',t);self.assertIn('if not state.get("validation_lock")',t);self.assertIn('if not state.get("internal_validation")',t)
