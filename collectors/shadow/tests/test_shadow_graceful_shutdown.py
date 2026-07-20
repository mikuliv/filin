import unittest
from collectors.shadow.tests.checks import check
class ShadowCheck(unittest.TestCase):
 def test_graceful_shutdown(self): check('graceful_shutdown')
