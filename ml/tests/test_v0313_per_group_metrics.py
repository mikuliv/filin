import unittest
from ml.tests.v0313_checks import check


class CheckV0313(unittest.TestCase):
    def test_per_group_metrics(self): check("per_group_metrics")

