import unittest
from v038_support import ROOT
class TestStageRunner(unittest.TestCase):
 def test_resume_skips_frozen_phases(self):
  text=(ROOT/'ml/experiments/v0_3_8/run_v0_3_8_stage.py').read_text(encoding='utf8');self.assertIn('if not state.get("nested_cv")',text);self.assertIn('if not state.get("validation_lock")',text);self.assertIn('if not state.get("internal_validation")',text)
