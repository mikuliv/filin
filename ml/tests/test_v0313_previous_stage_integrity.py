import unittest
from ml.tests.v0313_checks import check


class CheckV0313(unittest.TestCase):
    def test_previous_stage_integrity(self): check("previous_stage_integrity")

