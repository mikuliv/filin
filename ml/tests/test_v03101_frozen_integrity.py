import unittest
from ml.tests._v03101_support import ROOT
from ml.audits.v0_3_10_1.frozen_integrity_audit import audit
class TestFrozenIntegrity(unittest.TestCase):
 def test_hash_gate(self): self.assertTrue(audit(ROOT,ROOT/"ml/audits/v0_3_10_1/audit_protocol.yaml")["frozen_integrity_passed"])
