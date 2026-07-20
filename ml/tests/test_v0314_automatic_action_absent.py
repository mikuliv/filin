import unittest
from ml.tests.v0314_checks import check
class V0314Check(unittest.TestCase):
 def test_automatic_action_absent(self): check('automatic_action_absent')
