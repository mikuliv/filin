import unittest
from v037_support import ROOT
class TestStageRunner(unittest.TestCase):
 def test_resume_forwarded_to_all_irreversible_phases(self):
  text=(ROOT/'ml/experiments/v0_3_7/run_v0_3_7_stage.py').read_text(encoding='utf8');self.assertGreaterEqual(text.count("'--resume'"),4);self.assertIn("if not state.get('nested_cv')",text);self.assertIn("if not state.get('internal_validation')",text)
