import unittest
from ml.tests.v0314_checks import check
class V0314Check(unittest.TestCase):
 def test_backend_write_absent(self): check('backend_write_absent')
