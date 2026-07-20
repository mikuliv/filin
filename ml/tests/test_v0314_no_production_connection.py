import unittest
from ml.tests.v0314_checks import check
class V0314Check(unittest.TestCase):
 def test_no_production_connection(self): check('no_production_connection')
