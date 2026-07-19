import unittest
from ml.tests.v0313_checks import check


class CheckV0313(unittest.TestCase):
    def test_readiness(self): check("readiness")

