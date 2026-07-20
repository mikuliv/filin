import unittest
from ml.tests.v0314_checks import check
class V0314Check(unittest.TestCase):
 def test_logging_redaction(self): check('logging_redaction')
