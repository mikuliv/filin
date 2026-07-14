import unittest
from network_sensor_v0_6 import EVIDENCE_ORDER
from v038_leakage_audit import audit
class TestLeakageAudit(unittest.TestCase):
 def test_profile_clean(self):self.assertTrue(audit(EVIDENCE_ORDER)['v038_leakage_audit_valid'])
 def test_label_rejected(self):self.assertFalse(audit(EVIDENCE_ORDER+['label'])['v038_leakage_audit_valid'])
