import unittest
from v0310_support import ROOT
class TestStage(unittest.TestCase):
 def test_resume(self):self.assertIn('--resume',(ROOT/'ml/experiments/v0_3_10/run_v0_3_10_stage.py').read_text(encoding='utf8'))

