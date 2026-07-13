import unittest
from v037_support import *
from v037_leakage_audit import audit
from network_sensor_v0_5 import CONTEXTUAL_ORDER
class TestLeakageAudit(unittest.TestCase):
 def test_metadata_absent(self):self.assertTrue(audit(CONTEXTUAL_ORDER)['v037_leakage_valid']);self.assertFalse(audit(CONTEXTUAL_ORDER+['label'])['v037_leakage_valid'])
