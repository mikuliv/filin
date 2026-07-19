import unittest
from ml.tests.v0313_checks import check


class CheckV0313(unittest.TestCase):
    def test_causal_sort(self): check("causal_sort")

