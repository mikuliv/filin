import unittest
from ml.tests.v0314_checks import check
class V0314Check(unittest.TestCase):
 def test_crash_consistency(self): check('crash_consistency')
