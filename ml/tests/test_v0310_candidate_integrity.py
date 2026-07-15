import unittest
from v0310_support import ROOT
class TestIntegrity(unittest.TestCase):
 def test_hash_check(self):self.assertIn('gate_artifact_sha256',(ROOT/'ml/experiments/v0_3_10/run_internal_validation.py').read_text(encoding='utf8'))

