import unittest
from collectors.shadow.tests.checks import check
class ShadowCheck(unittest.TestCase):
 def test_mock_sink(self): check('mock_sink')
