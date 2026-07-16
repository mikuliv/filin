import unittest,yaml
from ml.tests._v03101_support import ROOT
class TestDataUsage(unittest.TestCase):
 def test_old_data_forbidden(self):
  p=yaml.safe_load((ROOT/"ml/audits/v0_3_10_1/audit_protocol.yaml").read_text(encoding="utf-8"));self.assertFalse(p["old_benchmark_access_allowed"]);self.assertTrue(p["forbidden_roots"])
