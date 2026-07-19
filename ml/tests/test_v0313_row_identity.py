import unittest
from ml.tests.v0313_checks import check


class CheckV0313(unittest.TestCase):
    def test_row_identity(self): check("row_identity")

