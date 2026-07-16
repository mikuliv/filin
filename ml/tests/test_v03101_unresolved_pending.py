import unittest
from ml.tests._v03101_support import semantics
class TestUnresolved(unittest.TestCase):
 def test_zero(self): self.assertEqual(semantics()["unresolved_pending_count"],0)
