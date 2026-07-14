import unittest
from v038_support import ROOT
class TestStageRunner(unittest.TestCase):
 def test_resume_skips_frozen_phases(self):
  text=(ROOT/'ml/experiments/v0_3_8/run_v0_3_8_stage.py').read_text(encoding='utf8');self.assertIn('if not state.get("nested_cv")',text);self.assertIn('if not state.get("validation_lock")',text);self.assertIn('if not state.get("internal_validation")',text)
 def test_sensor_children_do_not_depend_on_parent_stdout(self):
  text=(ROOT/'lab/campaigns/v038_runner.py').read_text(encoding='utf8');self.assertIn('capture_output=True',text);self.assertIn('Sensor subprocess завершился',text)
