import unittest
from collectors.shadow.tests.checks import check
class ShadowCheck(unittest.TestCase):
 def test_duplicate_delivery(self): check('duplicate_delivery')
