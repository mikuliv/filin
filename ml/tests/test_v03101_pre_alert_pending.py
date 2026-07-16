import unittest
from ml.tests._v03101_support import semantics
class TestPreAlert(unittest.TestCase):
 def test_none(self): self.assertEqual(semantics()["pre_alert_pending_count"],0)
