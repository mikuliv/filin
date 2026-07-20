import unittest
from ml.tests.v0314_checks import check
class V0314Check(unittest.TestCase):
 def test_candidate_integrity(self): check('candidate_integrity')
