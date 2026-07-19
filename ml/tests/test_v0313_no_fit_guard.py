import unittest
from ml.tests.v0313_checks import check


class CheckV0313(unittest.TestCase):
    def test_no_fit_guard(self): check("no_fit_guard")

