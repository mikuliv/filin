import unittest
from ml.tests.v0313_checks import check


class CheckV0313(unittest.TestCase):
    def test_performance_profile(self): check("performance_profile")

