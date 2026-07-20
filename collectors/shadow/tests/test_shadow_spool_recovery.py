import unittest
from collectors.shadow.tests.checks import check
class ShadowCheck(unittest.TestCase):
 def test_spool_recovery(self): check('spool_recovery')
