import unittest,yaml
from ml.tests._v03101_support import ROOT
class TestProtocol(unittest.TestCase):
 def test_read_only(self):
  p=yaml.safe_load((ROOT/"ml/audits/v0_3_10_1/audit_protocol.yaml").read_text(encoding="utf-8"));self.assertFalse(p["refit_allowed"]);self.assertEqual(len(p["expected_frozen_hashes"]),12)
