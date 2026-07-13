import unittest
from ml.tests.v036_test_utils import ROOT
class StageRunnerTests(unittest.TestCase):
 def test_resume_does_not_run_campaign(self):
  text=(ROOT/'lab/holdout/run_v0_3_6_stage.py').read_text(encoding='utf-8');self.assertIn("campaign_rerun_performed",text);self.assertNotIn('run_v034_campaign',text)
