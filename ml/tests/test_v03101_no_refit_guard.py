import unittest
from ml.audits.v0_3_10_1.no_refit_guard import NoRefitGuard
class TestNoRefit(unittest.TestCase):
 def test_report_zero(self): self.assertTrue(NoRefitGuard().report()["no_refit_audit_passed"])
 def test_block_fails(self):
  g=NoRefitGuard()
  with self.assertRaises(RuntimeError): g.block("fit")
  self.assertEqual(g.report()["fit_call_count"],1)
