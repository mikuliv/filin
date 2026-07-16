import unittest
from ml.tests._v03101_support import semantics
class TestContinuation(unittest.TestCase):
 def test_count(self): self.assertEqual(semantics()["post_alert_continuation_count"],120)
