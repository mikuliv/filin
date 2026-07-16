import unittest
from ml.tests._v03101_support import ROOT
class TestRunner(unittest.TestCase):
 def test_cli_contract(self):
  t=(ROOT/"ml/audits/v0_3_10_1/run_v0_3_10_1_audit.py").read_text(encoding="utf-8");self.assertIn("--strict",t);self.assertIn("--resume",t);self.assertIn("for workers in (1,3,6,8)",t)
